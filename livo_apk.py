"""
LIVO APK builder — собирает Android-приложение (WebView-обёртка сайта) на чистом Python.
Не нужны Android SDK, Java или Gradle: нужен только пакет `cryptography` (для подписи).

CLI:
    python livo_apk.py https://твой-сайт.onrender.com            -> LIVO.apk
    python livo_apk.py https://твой-сайт.onrender.com -o out.apk

Из кода (используется Flask-маршрутом /livo.apk):
    from livo_apk import build_apk
    data = build_apk("https://твой-сайт.onrender.com")
"""
import hashlib
import os
import re
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "apk_assets"

PACKAGE = "com.livo.app"
APP_LABEL = "LIVO"
VERSION_CODE = 1
VERSION_NAME = "1.0"
MIN_SDK = 24      # v2-подпись есть с Android 7.0
TARGET_SDK = 34
BG_COLOR = 0xFF050509  # как theme-color сайта


# ───────────────────────────── helpers ─────────────────────────────
def uleb(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def mutf8(s):
    """Modified UTF-8 + число UTF-16 единиц (формат строк в DEX)."""
    raw = s.encode("utf-16-le")
    units = struct.unpack("<%dH" % (len(raw) // 2), raw)
    out = bytearray()
    for u in units:
        if u == 0:
            out += b"\xc0\x80"
        elif u < 0x80:
            out.append(u)
        elif u < 0x800:
            out += bytes([0xC0 | (u >> 6), 0x80 | (u & 0x3F)])
        else:
            out += bytes([0xE0 | (u >> 12), 0x80 | ((u >> 6) & 0x3F), 0x80 | (u & 0x3F)])
    return bytes(out), len(units)


def pad4(b):
    return b + b"\x00" * ((-len(b)) % 4)


# ───────────────────────────── DEX ─────────────────────────────
OPS = {
    "move-result": 0x0A, "move-result-object": 0x0C, "return-void": 0x0E, "return": 0x0F,
    "move-object": 0x07, "const/4": 0x12, "const": 0x14, "const-string": 0x1A, "new-instance": 0x22,
    "new-array": 0x23, "aput-object": 0x4D, "iget-object": 0x54, "iput-object": 0x5B,
    "sget-object": 0x62, "sput-object": 0x69, "invoke-virtual": 0x6E, "invoke-super": 0x6F,
    "invoke-direct": 0x70, "invoke-static": 0x71, "invoke-interface": 0x72,
    "invoke-virtual/range": 0x74, "if-ne": 0x33, "if-eqz": 0x38, "if-nez": 0x39,
}
SIZES = {
    "move-result": 1, "move-result-object": 1, "return-void": 1, "return": 1, "move-object": 1,
    "const/4": 1, "const": 3, "const-string": 2, "new-instance": 2, "new-array": 2,
    "aput-object": 2, "iget-object": 2, "iput-object": 2, "sget-object": 2, "sput-object": 2,
    "invoke-virtual": 3, "invoke-super": 3, "invoke-direct": 3, "invoke-static": 3,
    "invoke-interface": 3, "invoke-virtual/range": 3, "if-ne": 2, "if-eqz": 2, "if-nez": 2,
}


def parse_sig(sig):
    """'(ILjava/lang/String;)V' -> (['I','Ljava/lang/String;'], 'V')"""
    assert sig[0] == "("
    close = sig.index(")")
    params, i, body = [], 0, sig[1:close]
    while i < len(body):
        j = i
        while body[j] == "[":
            j += 1
        if body[j] == "L":
            j = body.index(";", j)
        params.append(body[i:j + 1])
        i = j + 1
    return params, sig[close + 1:]


def shorty_char(t):
    return "L" if t[0] in "L[" else t


class M:
    """Метод класса: код — список инструкций (кортежей) и меток (строки вида ':name')."""

    def __init__(self, name, sig, flags, regs, ins, outs, code):
        self.name, self.sig, self.flags = name, sig, flags
        self.regs, self.ins, self.outs, self.code = regs, ins, outs, code


class C:
    def __init__(self, name, sup, static_fields=(), inst_fields=(), direct=(), virtual=()):
        self.name, self.sup = name, sup
        self.static_fields, self.inst_fields = list(static_fields), list(inst_fields)
        self.direct, self.virtual = list(direct), list(virtual)


def build_dex(classes):
    # 1. собираем все ссылки
    strings, types, fields, methods = set(), set(), set(), set()

    def add_type(t):
        types.add(t)
        strings.add(t)

    def add_method(ref):
        cls, name, sig = ref
        add_type(cls)
        strings.add(name)
        params, ret = parse_sig(sig)
        for t in params + [ret]:
            add_type(t)
        strings.add(sig_shorty(sig))
        methods.add(ref)

    def sig_shorty(sig):
        params, ret = parse_sig(sig)
        return shorty_char(ret) + "".join(shorty_char(p) for p in params)

    def add_field(ref):
        cls, name, typ = ref
        add_type(cls)
        add_type(typ)
        strings.add(name)
        fields.add(ref)

    for c in classes:
        add_type(c.name)
        add_type(c.sup)
        for n, t, _ in c.static_fields + c.inst_fields:
            add_field((c.name, n, t))
        for m in c.direct + c.virtual:
            add_method((c.name, m.name, m.sig))
            for ins in m.code:
                if isinstance(ins, str):
                    continue
                for a in ins[1:]:
                    if isinstance(a, tuple) and a[0] == "S":
                        strings.add(a[1])
                    elif isinstance(a, tuple) and a[0] == "T":
                        add_type(a[1])
                    elif isinstance(a, tuple) and a[0] == "F":
                        add_field(a[1])
                    elif isinstance(a, tuple) and a[0] == "M":
                        add_method(a[1])

    skey = lambda s: s.encode("utf-16-be")
    str_list = sorted(strings, key=skey)
    sidx = {s: i for i, s in enumerate(str_list)}
    type_list = sorted(types, key=lambda t: sidx[t])
    tidx = {t: i for i, t in enumerate(type_list)}

    def proto_of(sig):
        params, ret = parse_sig(sig)
        return (tidx[ret], tuple(tidx[p] for p in params), sig)

    protos = {}
    for (_, _, sig) in methods:
        p = proto_of(sig)
        protos[(p[0], p[1])] = sig
    proto_list = sorted(protos.keys())
    pidx = {k: i for i, k in enumerate(proto_list)}

    field_list = sorted(fields, key=lambda f: (tidx[f[0]], sidx[f[1]], tidx[f[2]]))
    fidx = {f: i for i, f in enumerate(field_list)}

    def mkey(m):
        p = proto_of(m[2])
        return (tidx[m[0]], sidx[m[1]], pidx[(p[0], p[1])])

    method_list = sorted(methods, key=mkey)
    midx = {m: i for i, m in enumerate(method_list)}

    # 2. раскладка
    n_s, n_t, n_p, n_f, n_m, n_c = len(str_list), len(type_list), len(proto_list), len(field_list), len(method_list), len(classes)
    off_s = 0x70
    off_t = off_s + 4 * n_s
    off_p = off_t + 4 * n_t
    off_f = off_p + 12 * n_p
    off_m = off_f + 8 * n_f
    off_c = off_m + 8 * n_m
    data_off = off_c + 32 * n_c

    data = bytearray()

    def pos():
        return data_off + len(data)

    def align(n):
        while len(data) % n:
            data.append(0)

    # string_data
    str_offs = []
    str_section_off = pos()
    for s in str_list:
        str_offs.append(pos())
        b, n = mutf8(s)
        data += uleb(n) + b + b"\x00"

    # type_lists
    align(4)
    tl_off = {}
    tl_start = pos()
    tl_count = 0
    for key in proto_list:
        params = key[1]
        if params and params not in tl_off:
            tl_off[params] = pos()
            tl_count += 1
            data += struct.pack("<I", len(params)) + b"".join(struct.pack("<H", t) for t in params)
            align(4)
    tl_end = pos()

    # code_items
    align(4)
    code_start = pos()
    code_off = {}
    code_count = 0

    def encode_code(m, owner):
        # размеры и метки
        labels, off = {}, 0
        for ins in m.code:
            if isinstance(ins, str):
                labels[ins] = off
            else:
                off += SIZES[ins[0]]
        units, off = [], 0
        for ins in m.code:
            if isinstance(ins, str):
                continue
            op = ins[0]
            code = OPS[op]
            a = ins[1:]
            here = off
            if op == "return-void":
                u = [code]
            elif op in ("move-result", "move-result-object", "return"):
                u = [code | (a[0] << 8)]
            elif op == "move-object":
                u = [code | (a[0] << 8) | (a[1] << 12)]
            elif op == "const/4":
                assert -8 <= a[1] <= 7 and a[0] < 16
                u = [code | (a[0] << 8) | ((a[1] & 0xF) << 12)]
            elif op == "const":
                v = a[1] & 0xFFFFFFFF
                u = [code | (a[0] << 8), v & 0xFFFF, v >> 16]
            elif op == "const-string":
                u = [code | (a[0] << 8), sidx[a[1][1]]]
            elif op in ("new-instance",):
                u = [code | (a[0] << 8), tidx[a[1][1]]]
            elif op == "new-array":
                assert a[0] < 16 and a[1] < 16
                u = [code | (a[0] << 8) | (a[1] << 12), tidx[a[2][1]]]
            elif op == "aput-object":
                u = [code | (a[0] << 8), a[1] | (a[2] << 8)]
            elif op in ("iget-object", "iput-object"):
                assert a[0] < 16 and a[1] < 16
                u = [code | (a[0] << 8) | (a[1] << 12), fidx[a[2][1]]]
            elif op in ("sget-object", "sput-object"):
                u = [code | (a[0] << 8), fidx[a[1][1]]]
            elif op in ("invoke-virtual", "invoke-super", "invoke-direct", "invoke-static", "invoke-interface"):
                regs, ref = a[0], a[1][1]
                assert len(regs) <= 5 and all(r < 16 for r in regs)
                r = list(regs) + [0] * (5 - len(regs))
                u = [code | (len(regs) << 12) | (r[4] << 8), midx[ref],
                     r[0] | (r[1] << 4) | (r[2] << 8) | (r[3] << 12)]
            elif op == "invoke-virtual/range":
                first, count, ref = a[0], a[1], a[2][1]
                u = [code | (count << 8), midx[ref], first]
            elif op in ("if-eqz", "if-nez"):
                rel = labels[a[1]] - here
                u = [code | (a[0] << 8), rel & 0xFFFF]
            elif op == "if-ne":
                rel = labels[a[2]] - here
                u = [code | (a[0] << 8) | (a[1] << 12), rel & 0xFFFF]
            else:
                raise ValueError(op)
            assert len(u) == SIZES[op], (op, len(u))
            units += u
            off += len(u)
        return units

    for c in classes:
        for m in c.direct + c.virtual:
            units = encode_code(m, c)
            align(4)
            code_off[(c.name, m.name, m.sig)] = pos()
            code_count += 1
            data += struct.pack("<HHHHII", m.regs, m.ins, m.outs, 0, 0, len(units))
            data += b"".join(struct.pack("<H", u) for u in units)
    code_end = pos()

    # class_data
    cd_off = {}
    cd_start = pos()
    cd_count = 0
    for c in classes:
        cd_off[c.name] = pos()
        cd_count += 1
        sf = sorted(c.static_fields, key=lambda f: fidx[(c.name, f[0], f[1])])
        inf = sorted(c.inst_fields, key=lambda f: fidx[(c.name, f[0], f[1])])
        dm = sorted(c.direct, key=lambda m: midx[(c.name, m.name, m.sig)])
        vm = sorted(c.virtual, key=lambda m: midx[(c.name, m.name, m.sig)])
        data += uleb(len(sf)) + uleb(len(inf)) + uleb(len(dm)) + uleb(len(vm))
        for group in (sf, inf):
            prev = 0
            for n, t, fl in group:
                i = fidx[(c.name, n, t)]
                data += uleb(i - prev) + uleb(fl)
                prev = i
        for group in (dm, vm):
            prev = 0
            for m in group:
                ref = (c.name, m.name, m.sig)
                i = midx[ref]
                data += uleb(i - prev) + uleb(m.flags) + uleb(code_off[ref])
                prev = i
    cd_end = pos()

    # map_list
    align(4)
    map_off = pos()
    items = [(0x0000, 1, 0), (0x0001, n_s, off_s), (0x0002, n_t, off_t), (0x0003, n_p, off_p),
             (0x0004, n_f, off_f), (0x0005, n_m, off_m), (0x0006, n_c, off_c),
             (0x2002, n_s, str_section_off)]
    if tl_count:
        items.append((0x1001, tl_count, tl_start))
    items += [(0x2001, code_count, code_start), (0x2000, cd_count, cd_start), (0x1000, 1, map_off)]
    items = [i for i in items if i[1]]
    items.sort(key=lambda i: i[2])
    data += struct.pack("<I", len(items))
    for t, n, o in items:
        data += struct.pack("<HHII", t, 0, n, o)
    align(4)

    # id-таблицы
    hdr_body = bytearray()
    for o in str_offs:
        hdr_body += struct.pack("<I", o)
    for t in type_list:
        hdr_body += struct.pack("<I", sidx[t])
    for key in proto_list:
        sig = protos[key]
        params = key[1]
        hdr_body += struct.pack("<III", sidx[sig_shorty(sig)], key[0], tl_off[params] if params else 0)
    for (cls, name, typ) in field_list:
        hdr_body += struct.pack("<HHI", tidx[cls], tidx[typ], sidx[name])
    for (cls, name, sig) in method_list:
        p = proto_of(sig)
        hdr_body += struct.pack("<HHI", tidx[cls], pidx[(p[0], p[1])], sidx[name])
    for c in classes:
        hdr_body += struct.pack("<IIIIIIII", tidx[c.name], 1, tidx[c.sup], 0, 0xFFFFFFFF, 0, cd_off[c.name], 0)

    file_size = data_off + len(data)
    header = bytearray(b"dex\n035\x00")
    header += b"\x00" * 4 + b"\x00" * 20  # checksum, signature (позже)
    header += struct.pack("<IIIIII", file_size, 0x70, 0x12345678, 0, 0, map_off)
    header += struct.pack("<IIIIIIIIIIIIII", n_s, off_s, n_t, off_t, n_p, off_p, n_f, off_f, n_m, off_m,
                          n_c, off_c, len(data), data_off)
    assert len(header) == 0x70, len(header)
    out = bytearray(header) + hdr_body + data
    assert len(out) == file_size
    out[12:32] = hashlib.sha1(bytes(out[32:])).digest()
    out[8:12] = struct.pack("<I", zlib.adler32(bytes(out[12:])) & 0xFFFFFFFF)
    return bytes(out)


# ───────── Smali-подобное описание приложения ─────────
def S(x): return ("S", x)
def T(x): return ("T", x)
def F(c, n, t): return ("F", (c, n, t))
def MR(c, n, s): return ("M", (c, n, s))


ACT = "Landroid/app/Activity;"
VIEW = "Landroid/webkit/WebView;"
VC = "Landroid/webkit/ValueCallback;"
INTENT = "Landroid/content/Intent;"
URI = "Landroid/net/Uri;"
STR = "Ljava/lang/String;"
MAIN = "Lcom/livo/app/MainActivity;"
CLIENT = "Lcom/livo/app/LivoClient;"
CHROME = "Lcom/livo/app/LivoChrome;"

PUBLIC, PROTECTED, PRIVATE, STATIC = 1, 4, 2, 8
CTOR = 0x10000


def offline_html(base):
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<style>html,body{height:100%;margin:0;background:#050509;color:#f7f7fb;"
        "font-family:sans-serif}body{display:flex;flex-direction:column;align-items:center;"
        "justify-content:center;text-align:center;padding:24px;box-sizing:border-box}"
        "h1{font-size:26px;margin:18px 0 8px}p{color:#989caf;margin:0 0 26px;line-height:1.5}"
        "a{display:inline-block;padding:14px 30px;border-radius:14px;color:#fff;"
        "text-decoration:none;font-weight:700;background:linear-gradient(135deg,#8b5cf6,#c026ff)}"
        ".l{font-size:54px;font-weight:900;letter-spacing:2px}</style></head><body>"
        '<div class="l">LIVO</div><h1>Нет подключения</h1>'
        "<p>Проверьте интернет и попробуйте ещё раз.</p>"
        '<a href="' + base + '">Повторить</a></body></html>'
    )


def app_classes(base):
    """base — например 'https://livo.onrender.com/' (со слэшем на конце)."""
    pending = F(MAIN, "pending", VC)
    web = F(MAIN, "web", VIEW)
    act_c = F(CLIENT, "act", ACT)
    act_h = F(CHROME, "act", ACT)

    # MainActivity.<init>
    main_init = M("<init>", "()V", PUBLIC | CTOR, 1, 1, 1, [
        ("invoke-direct", [0], MR(ACT, "<init>", "()V")),
        ("return-void",),
    ])

    # onCreate: this=v4, bundle=v5
    on_create = M("onCreate", "(Landroid/os/Bundle;)V", PROTECTED, 6, 2, 2, [
        ("invoke-super", [4, 5], MR(ACT, "onCreate", "(Landroid/os/Bundle;)V")),
        ("invoke-virtual", [4], MR(ACT, "getWindow", "()Landroid/view/Window;")),
        ("move-result-object", 0),
        ("const", 1, BG_COLOR),
        ("invoke-virtual", [0, 1], MR("Landroid/view/Window;", "setStatusBarColor", "(I)V")),
        ("invoke-virtual", [0, 1], MR("Landroid/view/Window;", "setNavigationBarColor", "(I)V")),
        ("new-instance", 2, T(VIEW)),
        ("invoke-direct", [2, 4], MR(VIEW, "<init>", "(Landroid/content/Context;)V")),
        ("invoke-virtual", [2, 1], MR(VIEW, "setBackgroundColor", "(I)V")),
        ("invoke-virtual", [2], MR(VIEW, "getSettings", "()Landroid/webkit/WebSettings;")),
        ("move-result-object", 3),
        ("const/4", 0, 1),
        ("invoke-virtual", [3, 0], MR("Landroid/webkit/WebSettings;", "setJavaScriptEnabled", "(Z)V")),
        ("invoke-virtual", [3, 0], MR("Landroid/webkit/WebSettings;", "setDomStorageEnabled", "(Z)V")),
        ("invoke-virtual", [3], MR("Landroid/webkit/WebSettings;", "getUserAgentString", "()" + STR)),
        ("move-result-object", 0),
        ("const-string", 1, S(" LIVOApp/" + VERSION_NAME)),
        ("invoke-virtual", [0, 1], MR(STR, "concat", "(" + STR + ")" + STR)),
        ("move-result-object", 0),
        ("invoke-virtual", [3, 0], MR("Landroid/webkit/WebSettings;", "setUserAgentString", "(" + STR + ")V")),
        ("new-instance", 0, T(CLIENT)),
        ("invoke-direct", [0, 4], MR(CLIENT, "<init>", "(" + ACT + ")V")),
        ("invoke-virtual", [2, 0], MR(VIEW, "setWebViewClient", "(Landroid/webkit/WebViewClient;)V")),
        ("new-instance", 0, T(CHROME)),
        ("invoke-direct", [0, 4], MR(CHROME, "<init>", "(" + ACT + ")V")),
        ("invoke-virtual", [2, 0], MR(VIEW, "setWebChromeClient", "(Landroid/webkit/WebChromeClient;)V")),
        ("iput-object", 2, 4, web),
        ("invoke-virtual", [4, 2], MR(ACT, "setContentView", "(Landroid/view/View;)V")),
        ("const-string", 0, S(base)),
        ("invoke-virtual", [2, 0], MR(VIEW, "loadUrl", "(" + STR + ")V")),
        ("return-void",),
    ])

    # onBackPressed: this=v2
    on_back = M("onBackPressed", "()V", PUBLIC, 3, 1, 1, [
        ("iget-object", 0, 2, web),
        ("invoke-virtual", [0], MR(VIEW, "canGoBack", "()Z")),
        ("move-result", 1),
        ("if-eqz", 1, ":exit"),
        ("invoke-virtual", [0], MR(VIEW, "goBack", "()V")),
        ("return-void",),
        ":exit",
        ("invoke-super", [2], MR(ACT, "onBackPressed", "()V")),
        ("return-void",),
    ])

    # onPause: this=v1
    on_pause = M("onPause", "()V", PROTECTED, 2, 1, 1, [
        ("invoke-super", [1], MR(ACT, "onPause", "()V")),
        ("invoke-static", [], MR("Landroid/webkit/CookieManager;", "getInstance", "()Landroid/webkit/CookieManager;")),
        ("move-result-object", 0),
        ("invoke-virtual", [0], MR("Landroid/webkit/CookieManager;", "flush", "()V")),
        ("return-void",),
    ])

    # onActivityResult(int,int,Intent): this=v4 req=v5 res=v6 data=v7
    on_result = M("onActivityResult", "(II" + INTENT + ")V", PROTECTED, 8, 4, 2, [
        ("sget-object", 0, pending),
        ("if-eqz", 0, ":end"),
        ("const/4", 1, 0),
        ("const/4", 2, -1),
        ("if-ne", 6, 2, ":send"),
        ("if-eqz", 7, ":send"),
        ("invoke-virtual", [7], MR(INTENT, "getData", "()" + URI)),
        ("move-result-object", 2),
        ("if-eqz", 2, ":send"),
        ("const/4", 3, 1),
        ("new-array", 1, 3, T("[" + URI)),
        ("const/4", 3, 0),
        ("aput-object", 2, 1, 3),
        ":send",
        ("invoke-interface", [0, 1], MR(VC, "onReceiveValue", "(Ljava/lang/Object;)V")),
        ("const/4", 0, 0),
        ("sput-object", 0, pending),
        ":end",
        ("return-void",),
    ])

    main = C(MAIN, ACT,
             static_fields=[("pending", VC, PUBLIC | STATIC)],
             inst_fields=[("web", VIEW, PRIVATE)],
             direct=[main_init], virtual=[on_create, on_back, on_pause, on_result])

    # LivoClient
    c_init = M("<init>", "(" + ACT + ")V", PUBLIC | CTOR, 2, 2, 1, [
        ("invoke-direct", [0], MR("Landroid/webkit/WebViewClient;", "<init>", "()V")),
        ("iput-object", 1, 0, act_c),
        ("return-void",),
    ])
    # shouldOverrideUrlLoading: this=v4 view=v5 url=v6
    c_override = M("shouldOverrideUrlLoading", "(" + VIEW + STR + ")Z", PUBLIC, 7, 3, 3, [
        ("const-string", 0, S(base)),
        ("invoke-virtual", [6, 0], MR(STR, "startsWith", "(" + STR + ")Z")),
        ("move-result", 0),
        ("if-nez", 0, ":no"),
        ("const-string", 0, S("http")),
        ("invoke-virtual", [6, 0], MR(STR, "startsWith", "(" + STR + ")Z")),
        ("move-result", 0),
        ("if-eqz", 0, ":no"),
        ("new-instance", 0, T(INTENT)),
        ("const-string", 1, S("android.intent.action.VIEW")),
        ("invoke-static", [6], MR(URI, "parse", "(" + STR + ")" + URI)),
        ("move-result-object", 2),
        ("invoke-direct", [0, 1, 2], MR(INTENT, "<init>", "(" + STR + URI + ")V")),
        ("iget-object", 1, 4, act_c),
        ("invoke-virtual", [1, 0], MR(ACT, "startActivity", "(" + INTENT + ")V")),
        ("const/4", 0, 1),
        ("return", 0),
        ":no",
        ("const/4", 0, 0),
        ("return", 0),
    ])
    # onReceivedError(view,int,String,String): this=v6 view=v7
    c_error = M("onReceivedError", "(" + VIEW + "I" + STR + STR + ")V", PUBLIC, 11, 5, 6, [
        ("move-object", 0, 7),
        ("const/4", 1, 0),
        ("const-string", 2, S(offline_html(base))),
        ("const-string", 3, S("text/html")),
        ("const-string", 4, S("UTF-8")),
        ("const/4", 5, 0),
        ("invoke-virtual/range", 0, 6, MR(VIEW, "loadDataWithBaseURL", "(" + STR * 5 + ")V")),
        ("return-void",),
    ])
    client = C(CLIENT, "Landroid/webkit/WebViewClient;", inst_fields=[("act", ACT, PRIVATE)],
               direct=[c_init], virtual=[c_override, c_error])

    # LivoChrome
    h_init = M("<init>", "(" + ACT + ")V", PUBLIC | CTOR, 2, 2, 1, [
        ("invoke-direct", [0], MR("Landroid/webkit/WebChromeClient;", "<init>", "()V")),
        ("iput-object", 1, 0, act_h),
        ("return-void",),
    ])
    # onShowFileChooser(view, cb, params): this=v4 view=v5 cb=v6 params=v7
    fcp = "Landroid/webkit/WebChromeClient$FileChooserParams;"
    h_chooser = M("onShowFileChooser", "(" + VIEW + VC + fcp + ")Z", PUBLIC, 8, 4, 3, [
        ("sget-object", 0, pending),
        ("if-eqz", 0, ":skip"),
        ("const/4", 1, 0),
        ("invoke-interface", [0, 1], MR(VC, "onReceiveValue", "(Ljava/lang/Object;)V")),
        ":skip",
        ("sput-object", 6, pending),
        ("new-instance", 0, T(INTENT)),
        ("const-string", 1, S("android.intent.action.GET_CONTENT")),
        ("invoke-direct", [0, 1], MR(INTENT, "<init>", "(" + STR + ")V")),
        ("const-string", 1, S("android.intent.category.OPENABLE")),
        ("invoke-virtual", [0, 1], MR(INTENT, "addCategory", "(" + STR + ")" + INTENT)),
        ("const-string", 1, S("image/*")),
        ("invoke-virtual", [0, 1], MR(INTENT, "setType", "(" + STR + ")" + INTENT)),
        ("const-string", 1, S(APP_LABEL)),
        ("invoke-static", [0, 1], MR(INTENT, "createChooser", "(" + INTENT + "Ljava/lang/CharSequence;)" + INTENT)),
        ("move-result-object", 0),
        ("iget-object", 1, 4, act_h),
        ("const/4", 2, 1),
        ("invoke-virtual", [1, 0, 2], MR(ACT, "startActivityForResult", "(" + INTENT + "I)V")),
        ("const/4", 0, 1),
        ("return", 0),
    ])
    chrome = C(CHROME, "Landroid/webkit/WebChromeClient;", inst_fields=[("act", ACT, PRIVATE)],
               direct=[h_init], virtual=[h_chooser])
    return [main, client, chrome]


# ───────────────────────────── Binary XML ─────────────────────────────
NS_ANDROID = "http://schemas.android.com/apk/res/android"
ATTR_ID = {
    "theme": 0x01010000, "label": 0x01010001, "icon": 0x01010002, "name": 0x01010003,
    "exported": 0x01010010, "configChanges": 0x0101001F, "minSdkVersion": 0x0101020C,
    "versionCode": 0x0101021B, "versionName": 0x0101021C, "windowSoftInputMode": 0x0101022B,
    "targetSdkVersion": 0x01010270, "allowBackup": 0x01010280, "drawable": 0x01010199,
    "usesCleartextTraffic": 0x010104EC, "roundIcon": 0x0101052C,
}
T_REF, T_STR, T_DEC, T_HEX, T_BOOL = 0x01, 0x03, 0x10, 0x11, 0x12


def string_pool(strings):
    """UTF-16 ResStringPool chunk."""
    blobs, offs, pos = [], [], 0
    for s in strings:
        b = struct.pack("<H", len(s)) + s.encode("utf-16-le") + b"\x00\x00"
        assert len(s) < 0x8000
        offs.append(pos)
        blobs.append(b)
        pos += len(b)
    body = b"".join(blobs)
    body = pad4(body)
    n = len(strings)
    strings_start = 28 + 4 * n
    size = strings_start + len(body)
    return (struct.pack("<HHIIIIII", 0x0001, 28, size, n, 0, 0, strings_start, 0)
            + b"".join(struct.pack("<I", o) for o in offs) + body)


class El:
    def __init__(self, tag, attrs=(), children=()):
        self.tag, self.attrs, self.children = tag, list(attrs), list(children)


def A(name, kind, value, ns=True):
    return (name, kind, value, ns)


def build_axml(root):
    # собираем строки: сначала имена атрибутов с resource id (по возрастанию id)
    def walk(e):
        yield e
        for c in e.children:
            yield from walk(c)

    id_names = sorted({a[0] for e in walk(root) for a in e.attrs if a[3]}, key=lambda n: ATTR_ID[n])
    pool = list(id_names)

    def S_(s):
        if s not in pool:
            pool.append(s)
        return pool.index(s)

    S_("android")
    S_(NS_ANDROID)
    for e in walk(root):
        S_(e.tag)
        for a in e.attrs:
            S_(a[0])
            if a[1] == "str":
                S_(a[2])
    ns_prefix, ns_uri = pool.index("android"), pool.index(NS_ANDROID)
    NONE = 0xFFFFFFFF

    nodes = bytearray()
    nodes += struct.pack("<HHIIIII", 0x0100, 16, 24, 1, NONE, ns_prefix, ns_uri)

    def emit(e, first=False):
        nonlocal nodes
        attrs = []
        for a in e.attrs:
            name, kind, val, has_ns = a
            ns = ns_uri if has_ns else NONE
            nm = pool.index(name)
            if kind == "str":
                sid = pool.index(val)
                attrs.append((ATTR_ID.get(name, 0xFFFFFFFF) if has_ns else 0xFFFFFFFF, ns, nm, sid, T_STR, sid))
            elif kind == "ref":
                attrs.append((ATTR_ID.get(name, 0xFFFFFFFF), ns, nm, NONE, T_REF, val))
            elif kind == "dec":
                attrs.append((ATTR_ID.get(name, 0xFFFFFFFF), ns, nm, NONE, T_DEC, val))
            elif kind == "hex":
                attrs.append((ATTR_ID.get(name, 0xFFFFFFFF), ns, nm, NONE, T_HEX, val))
            elif kind == "bool":
                attrs.append((ATTR_ID.get(name, 0xFFFFFFFF), ns, nm, NONE, T_BOOL, 0xFFFFFFFF if val else 0))
        # сортировка: с resource id по возрастанию, без id — в конце
        attrs.sort(key=lambda t: (t[0] == 0xFFFFFFFF, t[0]))
        size = 36 + 20 * len(attrs)
        nodes += struct.pack("<HHIIIIIHHHHHH", 0x0102, 16, size, 1, NONE, NONE, pool.index(e.tag),
                             0x14, 0x14, len(attrs), 0, 0, 0)
        for _, ns, nm, raw, dt, data in attrs:
            nodes += struct.pack("<IIIHBBI", ns, nm, raw, 8, 0, dt, data)
        for c in e.children:
            emit(c)
        nodes += struct.pack("<HHIIIII", 0x0103, 16, 24, 1, NONE, NONE, pool.index(e.tag))

    emit(root)
    nodes += struct.pack("<HHIIIII", 0x0101, 16, 24, 1, NONE, ns_prefix, ns_uri)

    pool_chunk = string_pool(pool)
    res_map = struct.pack("<HHI", 0x0180, 8, 8 + 4 * len(id_names)) + b"".join(
        struct.pack("<I", ATTR_ID[n]) for n in id_names)
    body = pool_chunk + res_map + bytes(nodes)
    return struct.pack("<HHI", 0x0003, 8, 8 + len(body)) + body


R_LAUNCHER, R_FG, R_BG = 0x7F010000, 0x7F010001, 0x7F010002


def manifest_xml(cleartext):
    app_attrs = [
        A("label", "str", APP_LABEL),
        A("icon", "ref", R_LAUNCHER),
        A("allowBackup", "bool", True),
        A("usesCleartextTraffic", "bool", cleartext),
    ]
    activity = El("activity", [
        A("name", "str", "com.livo.app.MainActivity"),
        A("exported", "bool", True),
        A("theme", "ref", 0x01030009),  # @android:style/Theme.Black.NoTitleBar
        A("configChanges", "hex", 0xFB0),
        A("windowSoftInputMode", "hex", 0x10),
    ], [El("intent-filter", [], [
        El("action", [A("name", "str", "android.intent.action.MAIN")]),
        El("category", [A("name", "str", "android.intent.category.LAUNCHER")]),
    ])])
    root = El("manifest", [
        A("versionCode", "dec", VERSION_CODE),
        A("versionName", "str", VERSION_NAME),
        A("package", "str", PACKAGE, ns=False),
    ], [
        El("uses-sdk", [A("minSdkVersion", "dec", MIN_SDK), A("targetSdkVersion", "dec", TARGET_SDK)]),
        El("uses-permission", [A("name", "str", "android.permission.INTERNET")]),
        El("application", app_attrs, [activity]),
    ])
    return build_axml(root)


def adaptive_icon_xml():
    root = El("adaptive-icon", [], [
        El("background", [A("drawable", "ref", R_BG)]),
        El("foreground", [A("drawable", "ref", R_FG)]),
    ])
    return build_axml(root)


# ───────────────────────────── resources.arsc ─────────────────────────────
def res_config(density=0, sdk=0):
    return struct.pack("<IIIBBHBBBBHHHHBBHHH", 36, 0, 0, 0, 0, density, 0, 0, 0, 0, 0, 0, sdk, 0, 0, 0, 0, 0, 0)


def build_arsc():
    P_PNG_L = "res/mipmap-xxxhdpi/ic_launcher.png"
    P_XML_L = "res/mipmap-anydpi-v26/ic_launcher.xml"
    P_FG = "res/mipmap-xxxhdpi/ic_fg.png"
    P_BG = "res/mipmap-xxxhdpi/ic_bg.png"
    values = [P_PNG_L, P_FG, P_BG, P_XML_L]
    keys = ["ic_launcher", "ic_fg", "ic_bg"]
    global_pool = string_pool(values)
    type_pool = string_pool(["mipmap"])
    key_pool = string_pool(keys)

    spec = struct.pack("<HHIBBHI", 0x0202, 16, 16 + 4 * 3, 1, 0, 0, 3)
    spec += struct.pack("<III", 0x40000400, 0x40000000, 0x40000000)  # public (+version differs for launcher)

    def type_chunk(config, entries):
        hdr = 20 + len(config)
        offs, body = [], b""
        for e in entries:
            if e is None:
                offs.append(0xFFFFFFFF)
            else:
                offs.append(len(body))
                body += struct.pack("<HHI", 8, 0, e[0]) + struct.pack("<HBBI", 8, 0, T_STR, e[1])
        entries_start = hdr + 4 * len(entries)
        size = entries_start + len(body)
        return (struct.pack("<HHI", 0x0201, hdr, size) + struct.pack("<BBHII", 1, 0, 0, len(entries), entries_start)
                + config + b"".join(struct.pack("<I", o) for o in offs) + body)

    default = type_chunk(res_config(), [(0, 0), (1, 1), (2, 2)])
    v26 = type_chunk(res_config(density=0xFFFE, sdk=26), [(0, 3), None, None])

    name = PACKAGE.encode("utf-16-le")
    name = name + b"\x00" * (256 - len(name))
    pkg_header_size = 288
    type_off = pkg_header_size
    key_off = type_off + len(type_pool)
    body = type_pool + key_pool + spec + default + v26
    pkg = (struct.pack("<HHI", 0x0200, pkg_header_size, pkg_header_size + len(body))
           + struct.pack("<I", 0x7F) + name + struct.pack("<IIIII", type_off, 1, key_off, len(keys), 0) + body)
    assert len(pkg) == pkg_header_size + len(body)
    table_body = global_pool + pkg
    return struct.pack("<HHII", 0x0002, 12, 12 + len(table_body), 1) + table_body


# ───────────────────────────── ZIP + подпись v2 ─────────────────────────────
DOS_TIME, DOS_DATE = 0, (44 << 9) | (1 << 5) | 1  # 2024-01-01


def build_zip(entries):
    """entries: [(name, bytes, stored?)] -> (entries_blob, central_dir, eocd_builder)"""
    out = bytearray()
    cd = bytearray()
    for name, data, stored in entries:
        nb = name.encode()
        crc = zlib.crc32(data) & 0xFFFFFFFF
        if stored:
            comp, method = data, 0
        else:
            c = zlib.compressobj(9, zlib.DEFLATED, -15)
            comp, method = c.compress(data) + c.flush(), 8
        off = len(out)
        extra = b""
        if stored:  # выравнивание данных по 4 байта (требование для resources.arsc)
            need = (-(off + 30 + len(nb))) % 4
            if need:
                n = need if need >= 4 else need + 4
                extra = struct.pack("<HH", 0xD935, n - 4) + b"\x00" * (n - 4)
        out += struct.pack("<IHHHHHIIIHH", 0x04034B50, 20, 0, method, DOS_TIME, DOS_DATE, crc, len(comp),
                           len(data), len(nb), len(extra)) + nb + extra + comp
        cd += struct.pack("<IHHHHHHIIIHHHHHII", 0x02014B50, 20, 20, 0, method, DOS_TIME, DOS_DATE, crc, len(comp),
                          len(data), len(nb), 0, 0, 0, 0, 0, off) + nb
    return bytes(out), bytes(cd)


def eocd(n_entries, cd_size, cd_offset):
    return struct.pack("<IHHHHIIH", 0x06054B50, 0, 0, n_entries, n_entries, cd_size, cd_offset, 0)


def load_signer():
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    import datetime

    pem = os.getenv("LIVO_APK_KEY_PEM")
    path = ASSETS / "livo_signing.pem"
    if not pem and path.exists():
        pem = path.read_text()
    if pem:
        key = serialization.load_pem_private_key(pem.encode(), None)
        cert = x509.load_pem_x509_certificate(pem.encode())
        return key, cert
    key = rsa.generate_private_key(65537, 2048)
    name = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "LIVO"),
                      x509.NameAttribute(x509.NameOID.ORGANIZATION_NAME, "LIVO")])
    now = datetime.datetime(2024, 1, 1)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=36500)).sign(key, hashes.SHA256()))
    pem = (key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                             serialization.NoEncryption()).decode()
           + cert.public_bytes(serialization.Encoding.PEM).decode())
    try:
        ASSETS.mkdir(exist_ok=True)
        path.write_text(pem)
    except OSError:
        pass
    return key, cert


def chunked_digest(sections):
    CH = 1 << 20
    digs = []
    for sec in sections:
        for i in range(0, max(len(sec), 1), CH):
            part = sec[i:i + CH]
            digs.append(hashlib.sha256(b"\xa5" + struct.pack("<I", len(part)) + part).digest())
    return hashlib.sha256(b"\x5a" + struct.pack("<I", len(digs)) + b"".join(digs)).digest()


def lp(b):
    return struct.pack("<I", len(b)) + b


def sign_v2(entries_blob, cd, n_entries):
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    key, cert = load_signer()
    cert_der = cert.public_bytes(serialization.Encoding.DER)
    pub_der = cert.public_key().public_bytes(serialization.Encoding.DER,
                                             serialization.PublicFormat.SubjectPublicKeyInfo)
    eocd_orig = eocd(n_entries, len(cd), len(entries_blob))
    digest = chunked_digest([entries_blob, cd, eocd_orig])
    ALGO = 0x0103  # RSASSA-PKCS1-v1_5 + SHA2-256
    signed_data = lp(lp(struct.pack("<I", ALGO) + lp(digest))) + lp(lp(cert_der)) + lp(b"")
    sig = key.sign(signed_data, padding.PKCS1v15(), hashes.SHA256())
    signer = lp(signed_data) + lp(lp(struct.pack("<I", ALGO) + lp(sig))) + lp(pub_der)
    v2_value = lp(lp(signer))
    pair = struct.pack("<QI", 4 + len(v2_value), 0x7109871A) + v2_value
    size = len(pair) + 8 + 16
    block = struct.pack("<Q", size) + pair + struct.pack("<Q", size) + b"APK Sig Block 42"
    return block


def validate_base(url):
    url = url.strip()
    m = re.fullmatch(r"(https?)://([A-Za-z0-9.-]+)(:\d{1,5})?/?", url)
    if not m:
        raise ValueError("URL должен быть вида https://домен (без пути и лишних символов)")
    return url.rstrip("/") + "/", m.group(1) == "http"


_cache = {}


def build_apk(url):
    base, cleartext = validate_base(url)
    if base in _cache:
        return _cache[base]
    dex = build_dex(app_classes(base))
    files = [
        ("AndroidManifest.xml", manifest_xml(cleartext), False),
        ("classes.dex", dex, False),
        ("resources.arsc", build_arsc(), True),
        ("res/mipmap-anydpi-v26/ic_launcher.xml", adaptive_icon_xml(), False),
        ("res/mipmap-xxxhdpi/ic_launcher.png", (ASSETS / "ic_launcher.png").read_bytes(), False),
        ("res/mipmap-xxxhdpi/ic_fg.png", (ASSETS / "ic_fg.png").read_bytes(), False),
        ("res/mipmap-xxxhdpi/ic_bg.png", (ASSETS / "ic_bg.png").read_bytes(), False),
    ]
    blob, cd = build_zip(files)
    block = sign_v2(blob, cd, len(files))
    apk = blob + block + cd + eocd(len(files), len(cd), len(blob) + len(block))
    if len(_cache) > 20:
        _cache.clear()
    _cache[base] = apk
    return apk


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Сборка LIVO.apk для твоего сайта")
    ap.add_argument("url", help="адрес сайта, например https://livo.onrender.com")
    ap.add_argument("-o", "--out", default="LIVO.apk")
    args = ap.parse_args()
    data = build_apk(args.url)
    Path(args.out).write_bytes(data)
    print("OK:", args.out, len(data), "bytes")
