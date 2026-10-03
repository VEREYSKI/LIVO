/* LIVO: тема, тосты, меню, анимации, живой поиск, избранное */
(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const csrf = () => ($('meta[name="csrf-token"]') || {}).content || '';
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const LOGGED = document.body.dataset.auth === '1';

  /* ---------- Тосты ---------- */
  const box = document.createElement('div');
  box.className = 'toasts'; box.setAttribute('aria-live', 'polite');
  document.body.appendChild(box);
  const ICONS = { success: '✅', error: '⚠️', info: '💜' };
  function toast(msg, type = 'info', opts = {}) {
    const ms = opts.duration || 4200;
    const el = document.createElement('div');
    el.className = 'toast ' + type; el.setAttribute('role', type === 'error' ? 'alert' : 'status');
    el.innerHTML = `<span class="t-icon">${ICONS[type] || ICONS.info}</span><div class="t-body">${esc(msg)}${
      opts.link ? `<br><a href="${esc(opts.link.href)}">${esc(opts.link.text)}</a>` : ''}</div>
      <button class="t-close" aria-label="Закрыть">×</button><i class="t-bar" style="animation-duration:${ms}ms"></i>`;
    const close = () => { if (el.classList.contains('leaving')) return; el.classList.add('leaving'); setTimeout(() => el.remove(), 250); };
    $('.t-close', el).onclick = close;
    el.onmouseenter = () => { clearTimeout(el._t); $('.t-bar', el).style.animationPlayState = 'paused'; };
    el.onmouseleave = () => { $('.t-bar', el).style.animationPlayState = 'running'; el._t = setTimeout(close, 1500); };
    el._t = setTimeout(close, ms);
    while (box.children.length >= 4) box.firstChild.remove();
    box.appendChild(el);
  }
  window.LIVO = { toast, esc };
  window.alert = (m) => toast(String(m), 'info'); // на случай старого кода
  (window.__FLASH || []).forEach(([t, m], i) => setTimeout(() => toast(m, t), 120 * i));

  /* ---------- Тема ---------- */
  const root = document.documentElement;
  function applyTheme(t) { root.dataset.theme = t; const m = $('meta[name="theme-color"]'); if (m) m.content = t === 'light' ? '#f4f2fb' : '#050509'; }
  $$('[data-theme-toggle]').forEach((b) => b.addEventListener('click', () => {
    const next = root.dataset.theme === 'light' ? 'dark' : 'light';
    root.classList.add('theme-anim'); applyTheme(next);
    try { localStorage.setItem('livo-theme', next); } catch (e) {}
    setTimeout(() => root.classList.remove('theme-anim'), 450);
    if (LOGGED) api('/api/theme', { theme: next }).catch(() => {});
    toast(next === 'light' ? 'Светлая тема ☀️' : 'Тёмная тема 🌙', 'info', { duration: 1800 });
  }));
  $$('input[name="theme"]').forEach((r) => r.addEventListener('change', () => {
    const v = r.value;
    try { v === 'auto' ? localStorage.removeItem('livo-theme') : localStorage.setItem('livo-theme', v); } catch (e) {}
    applyTheme(v === 'auto' ? (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark') : v);
  }));

  /* ---------- API ---------- */
  async function api(url, body) {
    const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf() }, body: JSON.stringify(body) });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) { const e = new Error(j.error || 'Ошибка запроса'); e.data = j; e.status = r.status; throw e; }
    return j;
  }

  /* ---------- Мобильное меню ---------- */
  const setMenu = (open) => document.body.classList.toggle('menu-open', open);
  $$('[data-menu-open]').forEach((b) => b.addEventListener('click', () => setMenu(true)));
  $$('[data-menu-close]').forEach((b) => b.addEventListener('click', () => setMenu(false)));
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { setMenu(false); const u = $('.user-menu'); if (u) u.open = false; } });
  document.addEventListener('click', (e) => { const u = $('.user-menu'); if (u && u.open && !u.contains(e.target)) u.open = false; });

  /* ---------- Анимация появления ---------- */
  const io = 'IntersectionObserver' in window ? new IntersectionObserver((es) => es.forEach((en) => {
    if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
  }), { rootMargin: '0px 0px -40px 0px', threshold: 0.05 }) : null;
  function reveal(scope = document) {
    $$('.reveal:not(.in)', scope).forEach((el, i) => {
      el.style.setProperty('--i', Math.min(i % 12, 11));
      io ? io.observe(el) : el.classList.add('in');
    });
  }
  window.LIVO.reveal = reveal; reveal();

  /* ---------- Избранное ---------- */
  const HEART = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s-7.5-4.6-9.6-9.2C.9 8.3 2.8 4.5 6.4 4.5c2 0 3.7 1.1 5.6 3.2 1.9-2.1 3.6-3.2 5.6-3.2 3.6 0 5.5 3.8 4 7.3C19.5 16.4 12 21 12 21z"/></svg>';
  window.LIVO.heart = HEART;
  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-fav]');
    if (!btn) return;
    e.preventDefault(); e.stopPropagation();
    if (btn.disabled) return;
    btn.disabled = true;
    try {
      const r = await api('/api/favorite', { kind: btn.dataset.kind, id: +btn.dataset.fav });
      btn.classList.toggle('on', r.favorited); btn.setAttribute('aria-pressed', r.favorited);
      btn.classList.remove('pop'); void btn.offsetWidth; btn.classList.add('pop');
      const lbl = $('.fav-label', btn); if (lbl) lbl.textContent = r.favorited ? 'В избранном' : 'В избранное';
      toast(r.favorited ? `«${r.title}» добавлено в избранное` : `«${r.title}» убрано из избранного`, r.favorited ? 'success' : 'info', { duration: 2600 });
      const card = btn.closest('[data-removable]');
      if (card && !r.favorited) { card.classList.add('removing'); setTimeout(() => card.remove(), 300); }
    } catch (err) {
      if (err.status === 401) toast(err.message, 'info', { link: { href: '/login?next=' + encodeURIComponent(location.pathname), text: 'Войти →' } });
      else toast(err.message, 'error');
    } finally { btn.disabled = false; }
  });

  /* ---------- Каталог с живым поиском ---------- */
  const PAL = (s) => { let h = 0; for (const c of s) h = (h * 31 + c.charCodeAt(0)) % 360; return h; };
  const EMOJI = { movie: ['🎬', '🍿', '🎞️', '⭐'], game: ['🎮', '🕹️', '👾', '🏆'] };
  function cardHTML(kind, it) {
    const h = PAL(it.title), em = EMOJI[kind][h % 4];
    const fav = `<button class="fav-btn ${it.fav ? 'on' : ''}" data-fav="${it.id}" data-kind="${kind}" aria-pressed="${it.fav}" aria-label="В избранное">${HEART}</button>`;
    const poster = `<div class="poster-ph" data-poster-title="${esc(it.title)}" data-poster-year="${it.year}" data-poster-kind="${kind}" style="--h:${h}">
      <span class="poster-loading">Загрузка…</span><span class="ph-emoji" aria-hidden="true">${em}</span><span class="ph-year">${it.year}</span>
    </div>`;
    if (kind === 'movie') return `<div class="card poster-card movie-card reveal">${fav}
      <a class="card-main" href="/movies/${it.id}">${poster}
      <b>${esc(it.title)}</b><span>${esc(it.genre)}</span>${it.rating && it.rating !== '—' ? `<small class="rating">★ ${esc(it.rating)}</small>` : ''}</a></div>`;
    return `<div class="card poster-card game-card reveal">${fav}<div class="card-main">${poster}
      <b>${esc(it.title)}</b><span>${esc(it.genre)}</span><small>${esc(it.platform)}</small></div></div>`;
  }
  /* ---------- Постеры фильмов и игр ---------- */
  const POSTER_CACHE_KEY = 'livo-poster-cache-v3';
  let POSTER_CACHE = {};
  try { POSTER_CACHE = JSON.parse(localStorage.getItem(POSTER_CACHE_KEY) || '{}'); } catch (e) {}

  function savePosterCache() {
    try { localStorage.setItem(POSTER_CACHE_KEY, JSON.stringify(POSTER_CACHE)); } catch (e) {}
  }

  const posterQueue = [];
  let posterActive = 0;
  function pumpPosters() {
    while (posterActive < 4 && posterQueue.length) {
      const job = posterQueue.shift();
      posterActive++;
      job().finally(() => { posterActive--; pumpPosters(); });
    }
  }

  // Ищем постер на сервере (он точнее подбирает фильм по названию и году). В кэш пишем только удачные ответы.
  function findPoster(title, year, kind) {
    const key = [kind || 'movie', String(title).trim().toLowerCase(), year || ''].join('|');
    if (POSTER_CACHE[key]) return Promise.resolve(POSTER_CACHE[key]);
    return new Promise((resolve) => {
      posterQueue.push(async () => {
        try {
          const p = new URLSearchParams({ title, year: year || '', kind: kind || 'movie' });
          const r = await fetch('/api/poster?' + p);
          if (!r.ok) throw new Error('poster request failed');
          const j = await r.json();
          if (j.url) { POSTER_CACHE[key] = j.url; savePosterCache(); }
          resolve(j.url || '');
        } catch (e) { resolve(''); }
      });
      pumpPosters();
    });
  }

  function applyPoster(el, src) {
    if (!el || !src) {
      if (el) el.classList.add('poster-fallback');
      return;
    }
    const img = new Image();
    img.onload = () => {
      el.style.setProperty('--poster-image', `url("${src.replace(/"/g, '\\"')}")`);
      el.classList.add('has-poster');
      const loading = $('.poster-loading', el);
      if (loading) loading.remove();
      const emoji = $('.ph-emoji', el);
      if (emoji) emoji.setAttribute('aria-hidden', 'true');
    };
    img.onerror = () => el.classList.add('poster-fallback');
    img.src = src;
  }

  const posterIO = 'IntersectionObserver' in window ? new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      const el = entry.target;
      posterIO.unobserve(el);
      const title = el.dataset.posterTitle;
      if (!title) return;
      findPoster(title, el.dataset.posterYear, el.dataset.posterKind).then(src => applyPoster(el, src));
    });
  }, { rootMargin: '180px' }) : null;

  async function loadPosters(scope = document) {
    const els = $$('.poster-ph[data-poster-title]:not([data-poster-watched])', scope);
    els.forEach(el => {
      el.dataset.posterWatched = '1';
      if (posterIO) posterIO.observe(el);
      else findPoster(el.dataset.posterTitle, el.dataset.posterYear, el.dataset.posterKind).then(src => applyPoster(el, src));
    });
  }

  window.LIVO.loadPosters = loadPosters;
  loadPosters();

  const skeleton = (kind, n = 12) => Array.from({ length: n }, () =>
    `<div class="card poster-card skeleton-card ${kind === 'game' ? 'game-skeleton' : ''}" aria-hidden="true"><span class="sk sk-poster"></span><span class="sk sk-line"></span><span class="sk sk-line short"></span></div>`).join('');

  const cat = $('[data-catalog]');
  if (cat) {
    const kind = cat.dataset.catalog, grid = $('#grid'), count = $('#count'), input = $('#q');
    const noun = kind === 'movie' ? ['фильм', 'фильма', 'фильмов'] : ['игра', 'игры', 'игр'];
    const plural = (n) => { const a = n % 100, b = n % 10; return a > 10 && a < 20 ? noun[2] : b === 1 ? noun[0] : b > 1 && b < 5 ? noun[1] : noun[2]; };
    let genre = 'all', ctrl, timer;
    async function load(first) {
      const q = input.value.trim();
      ctrl && ctrl.abort(); ctrl = new AbortController();
      const t0 = performance.now();
      if (first) grid.innerHTML = skeleton(kind); else grid.style.opacity = .55;
      try {
        const p = new URLSearchParams({ q }); if (kind === 'game') p.set('genre', genre);
        const r = await fetch(`/api/${kind}s?${p}`, { signal: ctrl.signal });
        if (!r.ok) throw new Error();
        const j = await r.json();
        const wait = first ? Math.max(0, 350 - (performance.now() - t0)) : 0; // чтобы skeleton не мигал
        setTimeout(() => {
          grid.style.opacity = 1;
          grid.innerHTML = j.items.length ? j.items.map((i) => cardHTML(kind, i)).join('') :
            `<div class="empty-state"><span class="big">🔍</span><h3>Ничего не найдено</h3><p>Попробуй другое название, жанр или год.</p><button class="btn btn-sm" data-reset>Сбросить поиск</button></div>`;
          if (window.LIVO && window.LIVO.translate) window.LIVO.translate(window.LIVO.getLanguage());
          loadPosters(grid);
          count.textContent = q || genre !== 'all' ? `Найдено: ${j.total}` : `${j.total} ${plural(j.total)}`;
          reveal(grid);
        }, wait);
        const u = new URL(location); q ? u.searchParams.set('q', q) : u.searchParams.delete('q'); history.replaceState(null, '', u);
      } catch (e) { if (e.name !== 'AbortError') { grid.style.opacity = 1; grid.innerHTML = ''; toast('Не удалось загрузить каталог. Проверь соединение.', 'error'); } }
    }
    input.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(() => load(false), 180); });
    $('#searchForm').addEventListener('submit', (e) => { e.preventDefault(); load(false); });
    document.addEventListener('click', (e) => { if (e.target.closest('[data-reset]')) { input.value = ''; genre = 'all'; $$('[data-genre]').forEach((c) => c.classList.toggle('active', c.dataset.genre === 'all')); load(false); input.focus(); } });
    $$('[data-genre]').forEach((c) => c.addEventListener('click', () => { genre = c.dataset.genre; $$('[data-genre]').forEach((x) => x.classList.toggle('active', x === c)); load(false); }));
    load(true);
  }

  /* ---------- Подсказки на главной ---------- */
  const hs = $('#heroSearch');
  if (hs) {
    const list = $('#suggest'); let t, sel = -1, ctrl;
    const hide = () => { list.hidden = true; sel = -1; };
    hs.addEventListener('input', () => {
      clearTimeout(t); const q = hs.value.trim();
      if (!q) return hide();
      t = setTimeout(async () => {
        ctrl && ctrl.abort(); ctrl = new AbortController();
        try {
          const j = await (await fetch('/api/movies?limit=5&q=' + encodeURIComponent(q), { signal: ctrl.signal })).json();
          list.innerHTML = j.items.map((m) => `<a href="/movies/${m.id}"><span>🎬 ${esc(m.title)}</span><small>${m.year}</small></a>`).join('') +
            `<a class="all" href="/movies?q=${encodeURIComponent(q)}">${j.total ? `Все результаты (${j.total}) →` : 'Ничего не найдено — открыть каталог →'}</a>`;
          list.hidden = false; sel = -1;
        } catch (e) {}
      }, 160);
    });
    hs.addEventListener('keydown', (e) => {
      const items = $$('a', list); if (list.hidden || !items.length) return;
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); sel = (sel + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length; items.forEach((a, i) => a.classList.toggle('sel', i === sel)); }
      else if (e.key === 'Enter' && sel > -1) { e.preventDefault(); location.href = items[sel].href; }
    });
    document.addEventListener('click', (e) => { if (!e.target.closest('.search-wrap')) hide(); });
  }

  /* ---------- Поиск друзей ---------- */
  const usInput = $('#userSearch');
  if (usInput) {
    const res = $('#userResults'), form = $('#userSearchForm');
    const logged = res.dataset.logged === '1';
    let t, ctrl;
    const card = (u, next) => {
      const ava = u.has_avatar
        ? `<img class="avatar avatar-md" src="/avatar/${u.id}?v=${u.avatar_v}" alt="">`
        : `<span class="avatar avatar-ph avatar-md">${esc((u.display_name || '?').trim().charAt(0).toUpperCase())}</span>`;
      const stats = u.show_stats ? `❤️ ${u.favs} · 👀 ${u.views}` : 'Статистика скрыта';
      const act = logged
        ? `<form method="post" action="/friends/${u.friend ? 'remove' : 'add'}/${u.id}"><input type="hidden" name="csrf_token" value="${esc(csrf())}"><input type="hidden" name="next" value="${esc(next)}"><button class="btn btn-sm ${u.friend ? 'btn-ghost' : 'btn-purple'}" type="submit">${u.friend ? 'Убрать из друзей' : 'Добавить в друзья'}</button></form>`
        : '';
      return `<div class="user-card"><a class="user-main" href="/u/${encodeURIComponent(u.username)}">${ava}<span class="user-info"><b>${esc(u.display_name)}</b><small>@${esc(u.username)}</small><small class="user-stats">${stats}</small></span></a>${act}</div>`;
    };
    async function run() {
      const q = usInput.value.trim();
      ctrl && ctrl.abort(); ctrl = new AbortController();
      if (q.length < 2) { res.innerHTML = '<p class="note">Введи минимум 2 символа.</p>'; return; }
      try {
        const r = await fetch('/api/users?q=' + encodeURIComponent(q), { signal: ctrl.signal });
        if (r.status === 429) { toast('Слишком много запросов. Подожди минуту.', 'error'); return; }
        if (!r.ok) throw new Error();
        const j = await r.json();
        const next = '/friends?q=' + encodeURIComponent(q);
        res.innerHTML = j.items.length ? j.items.map((u) => card(u, next)).join('')
          : '<div class="empty-state"><span class="big">🔍</span><h3>Никого не найдено</h3></div>';
        history.replaceState(null, '', next);
      } catch (e) { if (e.name !== 'AbortError') toast('Не удалось выполнить поиск. Проверь соединение.', 'error'); }
    }
    usInput.addEventListener('input', () => { clearTimeout(t); t = setTimeout(run, 220); });
    form.addEventListener('submit', (e) => { e.preventDefault(); run(); });
  }

  /* ---------- Формы ---------- */
  $$('.pw-toggle').forEach((b) => b.addEventListener('click', () => {
    const i = b.previousElementSibling; const show = i.type === 'password'; i.type = show ? 'text' : 'password'; b.textContent = show ? '🙈' : '👁️';
  }));
  $$('form[data-busy]').forEach((f) => f.addEventListener('submit', () => { const b = $('button[type=submit]', f); if (b) { b.disabled = true; b.textContent = 'Подождите…'; } }));
  const av = $('#avatarInput');
  if (av) av.addEventListener('change', () => {
    const f = av.files[0]; if (!f) return;
    if (f.size > 2 * 1024 * 1024) { toast('Файл слишком большой (максимум 2 МБ).', 'error'); av.value = ''; return; }
    if (!/^image\/(png|jpeg|webp|gif)$/.test(f.type)) { toast('Поддерживаются PNG, JPG, WEBP и GIF.', 'error'); av.value = ''; return; }
    av.form.submit();
  });
  $$('form[data-confirm]').forEach((f) => f.addEventListener('submit', (e) => {
    if (f.dataset.ok) return; e.preventDefault();
    if (f.dataset.confirm === 'password') { const i = $('input[name=password]', f); if (!i.value) { i.focus(); toast('Введи пароль для подтверждения.', 'error'); return; } }
    f.dataset.ok = 1; f.submit();
  }));
})();

/* ---------- Локализация LIVO ---------- */
(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const LANG_KEY = 'livo-language-v1';
  const LANGS = ['ru','en','de','fr','es','it','uk','pl','nl'];
  const T = {
    ru: {
      'Фильмы':'Фильмы','Игры':'Игры','Фитнес':'Фитнес','Челленджи':'Челленджи','ПК':'ПК','Рецепты':'Рецепты','Профиль':'Профиль','Избранное':'Избранное','История':'История','Настройки':'Настройки','Выйти':'Выйти','Войти':'Войти','Регистрация':'Регистрация','Мне скучно':'Мне скучно','Ещё':'Ещё','Главная':'Главная','О сайте':'О сайте','Конфиденциальность':'Конфиденциальность','Политика':'Политика','Социальные сети':'Социальные сети','Язык интерфейса':'Язык интерфейса','Тема':'Тема','Сохранить':'Сохранить','Удалить':'Удалить','Очистить':'Очистить','Открыть каталог':'Открыть каталог','В каталог →':'В каталог →','К фильмам':'К фильмам','Пока пусто':'Пока пусто','История пуста':'История пуста','Загрузить фото':'Загрузить фото','Аватар':'Аватар','Профиль':'Профиль','Отображаемое имя':'Отображаемое имя','Имя пользователя':'Имя пользователя','О себе':'О себе','Email':'Email','Смена пароля':'Смена пароля','Текущий пароль':'Текущий пароль','Новый пароль':'Новый пароль','Повтори новый пароль':'Повтори новый пароль','Удалить аккаунт':'Удалить аккаунт','Удалить навсегда':'Удалить навсегда','Пароль для подтверждения':'Пароль для подтверждения','Светлая':'Светлая','Тёмная':'Тёмная','Авто':'Авто','Все':'Все','Все жанры':'Все жанры','Ничего не найдено':'Ничего не найдено','Сбросить поиск':'Сбросить поиск','Найдено':'Найдено','Загрузка…':'Загрузка…','Загрузка постера…':'Загрузка постера…','Подождите…':'Подождите…','Рассчитать FPS':'Рассчитать FPS','Сбросить фильтры':'Сбросить фильтры','Популярные игры и новинки':'Популярные игры и новинки','Популярные игры':'Популярные игры','Фильмы и сериалы':'Фильмы и сериалы','Собери свою тренировку':'Собери свою тренировку','Получить случайную идею':'Получить случайную идею','Придумай':'Придумай','Тебе выпало':'Тебе выпало','Твой случайный челлендж':'Твой случайный челлендж','Очень просто':'Очень просто','Просто':'Просто','Средне':'Средне','Средний':'Средний','Продвинутый':'Продвинутый','Новичок':'Новичок','Сила':'Сила','Выносливость':'Выносливость','Набор мышц':'Набор мышц','Снижение веса':'Снижение веса','Спорт':'Спорт','Завтрак':'Завтрак','Обед':'Обед','Ужин':'Ужин','Перекус':'Перекус','Десерт':'Десерт','Гарниры':'Гарниры','Супы':'Супы','Гонки':'Гонки','Шутеры':'Шутеры','Стратегии':'Стратегии','Симуляторы':'Симуляторы','Выживание':'Выживание','Хорроры':'Хорроры','Кооператив':'Кооператив','Экшен':'Экшен','RPG':'RPG','Книга рецептов LIVO':'Книга рецептов LIVO','На главную':'На главную','← Все фильмы':'← Все фильмы','Весь каталог →':'Весь каталог →','Войти':'Войти','Создать аккаунт':'Создать аккаунт','Создай аккаунт ✨':'Создай аккаунт ✨','С возвращением 👋':'С возвращением 👋','Нет аккаунта? ':'Нет аккаунта? ','Уже есть аккаунт? ':'Уже есть аккаунт? ','Пароль':'Пароль','Минимум 8 символов':'Минимум 8 символов','Повтори пароль':'Повтори пароль','Изменить пароль':'Изменить пароль','Рейтинг':'Рейтинг','Сохранить':'Сохранить'
    },
    en: {
      'Приложение':'App','Фильмы':'Movies','Игры':'Games','Фитнес':'Fitness','Челленджи':'Challenges','ПК':'PC','Рецепты':'Recipes','Профиль':'Profile','Избранное':'Favorites','История':'History','Настройки':'Settings','Выйти':'Log out','Войти':'Log in','Регистрация':'Sign up','Мне скучно':'I’m bored','Ещё':'More','Главная':'Home','О сайте':'About','Конфиденциальность':'Privacy','Политика':'Policy','Социальные сети':'Social','Язык интерфейса':'Interface language','Тема':'Theme','Сохранить':'Save','Удалить':'Delete','Очистить':'Clear','Открыть каталог':'Open catalog','В каталог →':'To catalog →','К фильмам':'To movies','Пока пусто':'Nothing here yet','История пуста':'History is empty','Загрузить фото':'Upload photo','Аватар':'Avatar','Отображаемое имя':'Display name','Имя пользователя':'Username','О себе':'About me','Смена пароля':'Change password','Текущий пароль':'Current password','Новый пароль':'New password','Повтори новый пароль':'Repeat new password','Удалить аккаунт':'Delete account','Удалить навсегда':'Delete permanently','Пароль для подтверждения':'Password for confirmation','Светлая':'Light','Тёмная':'Dark','Авто':'Auto','Все':'All','Все жанры':'All genres','Ничего не найдено':'Nothing found','Сбросить поиск':'Reset search','Найдено':'Found','Загрузка…':'Loading…','Загрузка постера…':'Loading poster…','Подождите…':'Please wait…','Рассчитать FPS':'Calculate FPS','Сбросить фильтры':'Reset filters','Популярные игры и новинки':'Popular games and new releases','Популярные игры':'Popular games','Фильмы и сериалы':'Movies and series','Собери свою тренировку':'Build your workout','Получить случайную идею':'Get a random idea','Придумай':'Generate','Тебе выпало':'Your result','Твой случайный челлендж':'Your random challenge','Очень просто':'Very easy','Просто':'Easy','Средне':'Medium','Средний':'Intermediate','Продвинутый':'Advanced','Новичок':'Beginner','Сила':'Strength','Выносливость':'Endurance','Набор мышц':'Muscle gain','Снижение веса':'Weight loss','Спорт':'Sport','Завтрак':'Breakfast','Обед':'Lunch','Ужин':'Dinner','Перекус':'Snack','Десерт':'Dessert','Гарниры':'Side dishes','Супы':'Soups','Гонки':'Racing','Шутеры':'Shooters','Стратегии':'Strategy','Симуляторы':'Simulation','Выживание':'Survival','Хорроры':'Horror','Кооператив':'Co-op','Экшен':'Action','Книга рецептов LIVO':'LIVO Recipe Book','На главную':'Home','← Все фильмы':'← All movies','Весь каталог →':'Full catalog →','Создать аккаунт':'Create account','Создай аккаунт ✨':'Create account ✨','С возвращением 👋':'Welcome back 👋','Пароль':'Password','Минимум 8 символов':'At least 8 characters','Повтори пароль':'Repeat password','Изменить пароль':'Change password'
    },
    de: {'Приложение':'App','Фильмы':'Filme','Игры':'Spiele','Фитнес':'Fitness','Челленджи':'Challenges','ПК':'PC','Рецепты':'Rezepte','Профиль':'Profil','Избранное':'Favoriten','История':'Verlauf','Настройки':'Einstellungen','Выйти':'Abmelden','Войти':'Anmelden','Регистрация':'Registrieren','Мне скучно':'Mir ist langweilig','Ещё':'Mehr','Главная':'Startseite','О сайте':'Über LIVO','Конфиденциальность':'Datenschutz','Политика':'Richtlinie','Социальные сети':'Soziale Netzwerke','Язык интерфейса':'Oberflächensprache','Тема':'Design','Сохранить':'Speichern','Удалить':'Löschen','Очистить':'Leeren','Открыть каталог':'Katalog öffnen','В каталог →':'Zum Katalog →','Пока пусто':'Noch leer','История пуста':'Verlauf ist leer','Загрузить фото':'Foto hochladen','Отображаемое имя':'Anzeigename','Имя пользователя':'Benutzername','О себе':'Über mich','Смена пароля':'Passwort ändern','Текущий пароль':'Aktuelles Passwort','Новый пароль':'Neues Passwort','Удалить аккаунт':'Konto löschen','Все':'Alle','Все жанры':'Alle Genres','Ничего не найдено':'Nichts gefunden','Загрузка…':'Laden…','Загрузка постера…':'Poster wird geladen…','Светлая':'Hell','Тёмная':'Dunkel','Авто':'Auto','Сохранить':'Speichern'},
    fr: {'Приложение':'Application','Фильмы':'Films','Игры':'Jeux','Фитнес':'Fitness','Челленджи':'Défis','ПК':'PC','Рецепты':'Recettes','Профиль':'Profil','Избранное':'Favoris','История':'Historique','Настройки':'Paramètres','Выйти':'Se déconnecter','Войти':'Se connecter','Регистрация':'Inscription','Мне скучно':'Je m’ennuie','Ещё':'Plus','Главная':'Accueil','О сайте':'À propos','Конфиденциальность':'Confidentialité','Политика':'Politique','Социальные сети':'Réseaux sociaux','Язык интерфейса':'Langue de l’interface','Тема':'Thème','Сохранить':'Enregistrer','Удалить':'Supprimer','Очистить':'Effacer','Открыть каталог':'Ouvrir le catalogue','В каталог →':'Au catalogue →','Пока пусто':'Rien pour le moment','История пуста':'Historique vide','Загрузить фото':'Télécharger une photo','Отображаемое имя':'Nom affiché','Имя пользователя':'Nom d’utilisateur','О себе':'À propos de moi','Смена пароля':'Changer le mot de passe','Текущий пароль':'Mot de passe actuel','Новый пароль':'Nouveau mot de passe','Удалить аккаунт':'Supprimer le compte','Все':'Tous','Все жанры':'Tous les genres','Ничего не найдено':'Aucun résultat','Загрузка…':'Chargement…','Загрузка постера…':'Chargement de l’affiche…','Светлая':'Clair','Тёмная':'Sombre','Авто':'Auto'},
    es: {'Приложение':'Aplicación','Фильмы':'Películas','Игры':'Juegos','Фитнес':'Fitness','Челленджи':'Desafíos','ПК':'PC','Рецепты':'Recetas','Профиль':'Perfil','Избранное':'Favoritos','История':'Historial','Настройки':'Ajustes','Выйти':'Cerrar sesión','Войти':'Iniciar sesión','Регистрация':'Registrarse','Мне скучно':'Estoy aburrido','Ещё':'Más','Главная':'Inicio','О сайте':'Acerca de','Конфиденциальность':'Privacidad','Политика':'Política','Социальные сети':'Redes sociales','Язык интерфейса':'Idioma de la interfaz','Тема':'Tema','Сохранить':'Guardar','Удалить':'Eliminar','Очистить':'Limpiar','Открыть каталог':'Abrir catálogo','В каталог →':'Al catálogo →','Пока пусто':'Aún está vacío','История пуста':'El historial está vacío','Загрузить фото':'Subir foto','Отображаемое имя':'Nombre mostrado','Имя пользователя':'Nombre de usuario','О себе':'Sobre mí','Смена пароля':'Cambiar contraseña','Текущий пароль':'Contraseña actual','Новый пароль':'Nueva contraseña','Удалить аккаунт':'Eliminar cuenta','Все':'Todos','Все жанры':'Todos los géneros','Ничего не найдено':'No se encontró nada','Загрузка…':'Cargando…','Загрузка постера…':'Cargando póster…','Светлая':'Claro','Тёмная':'Oscuro','Авто':'Automático'},
    it: {'Приложение':'App','Фильмы':'Film','Игры':'Giochi','Фитнес':'Fitness','Челленджи':'Sfide','ПК':'PC','Рецепты':'Ricette','Профиль':'Profilo','Избранное':'Preferiti','История':'Cronologia','Настройки':'Impostazioni','Выйти':'Esci','Войти':'Accedi','Регистрация':'Registrati','Мне скучно':'Mi annoio','Ещё':'Altro','Главная':'Home','О сайте':'Informazioni','Конфиденциальность':'Privacy','Язык интерфейса':'Lingua interfaccia','Тема':'Tema','Сохранить':'Salva','Удалить':'Elimina','Очистить':'Cancella','Открыть каталог':'Apri catalogo','Пока пусто':'Ancora vuoto','История пуста':'Cronologia vuota','Загрузить фото':'Carica foto','Отображаемое имя':'Nome visualizzato','Имя пользователя':'Nome utente','О себе':'Su di me','Смена пароля':'Cambia password','Текущий пароль':'Password attuale','Новый пароль':'Nuova password','Удалить аккаунт':'Elimina account','Все':'Tutti','Все жанры':'Tutti i generi','Ничего не найдено':'Nessun risultato','Загрузка…':'Caricamento…','Загрузка постера…':'Caricamento poster…','Светлая':'Chiaro','Тёмная':'Scuro','Авто':'Auto'},
    uk: {'Приложение':'Застосунок','Фильмы':'Фільми','Игры':'Ігри','Фитнес':'Фітнес','Челленджи':'Челенджі','ПК':'ПК','Рецепты':'Рецепти','Профиль':'Профіль','Избранное':'Обране','История':'Історія','Настройки':'Налаштування','Выйти':'Вийти','Войти':'Увійти','Регистрация':'Реєстрація','Мне скучно':'Мені нудно','Ещё':'Ще','Главная':'Головна','О сайте':'Про сайт','Конфиденциальность':'Конфіденційність','Политика':'Політика','Социальные сети':'Соціальні мережі','Язык интерфейса':'Мова інтерфейсу','Тема':'Тема','Сохранить':'Зберегти','Удалить':'Видалити','Очистить':'Очистити','Открыть каталог':'Відкрити каталог','В каталог →':'До каталогу →','Пока пусто':'Поки порожньо','История пуста':'Історія порожня','Загрузить фото':'Завантажити фото','Отображаемое имя':'Відображуване ім’я','Имя пользователя':'Ім’я користувача','О себе':'Про себе','Смена пароля':'Змінити пароль','Текущий пароль':'Поточний пароль','Новый пароль':'Новий пароль','Удалить аккаунт':'Видалити акаунт','Все':'Усі','Все жанры':'Усі жанри','Ничего не найдено':'Нічого не знайдено','Загрузка…':'Завантаження…','Загрузка постера…':'Завантаження постера…','Светлая':'Світла','Тёмная':'Темна','Авто':'Авто'},
    pl: {'Приложение':'Aplikacja','Фильмы':'Filmy','Игры':'Gry','Фитнес':'Fitness','Челленджи':'Wyzwania','ПК':'PC','Рецепты':'Przepisy','Профиль':'Profil','Избранное':'Ulubione','История':'Historia','Настройки':'Ustawienia','Выйти':'Wyloguj','Войти':'Zaloguj','Регистрация':'Rejestracja','Мне скучно':'Nudzę się','Ещё':'Więcej','Главная':'Strona główna','О сайте':'O stronie','Конфиденциальность':'Prywatność','Политика':'Polityka','Социальные сети':'Media społecznościowe','Язык интерфейса':'Język interfejsu','Тема':'Motyw','Сохранить':'Zapisz','Удалить':'Usuń','Очистить':'Wyczyść','Открыть каталог':'Otwórz katalog','В каталог →':'Do katalogu →','Пока пусто':'Na razie pusto','История пуста':'Historia jest pusta','Загрузить фото':'Prześlij zdjęcie','Отображаемое имя':'Nazwa wyświetlana','Имя пользователя':'Nazwa użytkownika','О себе':'O mnie','Смена пароля':'Zmień hasło','Текущий пароль':'Aktualne hasło','Новый пароль':'Nowe hasło','Удалить аккаунт':'Usuń konto','Все':'Wszystko','Все жанры':'Wszystkie gatunki','Ничего не найдено':'Nic nie znaleziono','Загрузка…':'Ładowanie…','Загрузка постера…':'Ładowanie plakatu…','Светлая':'Jasny','Тёмная':'Ciemny','Авто':'Auto'},
    nl: {'Приложение':'App','Фильмы':'Films','Игры':'Games','Фитнес':'Fitness','Челленджи':'Uitdagingen','ПК':'PC','Рецепты':'Recepten','Профиль':'Profiel','Избранное':'Favorieten','История':'Geschiedenis','Настройки':'Instellingen','Выйти':'Uitloggen','Войти':'Inloggen','Регистрация':'Registreren','Мне скучно':'Ik verveel me','Ещё':'Meer','Главная':'Home','О сайте':'Over LIVO','Конфиденциальность':'Privacy','Политика':'Beleid','Социальные сети':'Sociale media','Язык интерфейса':'Interfacetaal','Тема':'Thema','Сохранить':'Opslaan','Удалить':'Verwijderen','Очистить':'Wissen','Открыть каталог':'Catalogus openen','В каталог →':'Naar catalogus →','Пока пусто':'Nog leeg','История пуста':'Geschiedenis is leeg','Загрузить фото':'Foto uploaden','Отображаемое имя':'Weergavenaam','Имя пользователя':'Gebruikersnaam','О себе':'Over mij','Смена пароля':'Wachtwoord wijzigen','Текущий пароль':'Huidig wachtwoord','Новый пароль':'Nieuw wachtwoord','Удалить аккаунт':'Account verwijderen','Все':'Alle','Все жанры':'Alle genres','Ничего не найдено':'Niets gevonden','Загрузка…':'Laden…','Загрузка постера…':'Poster laden…','Светлая':'Licht','Тёмная':'Donker','Авто':'Auto'}
  };

  /* Дополнительные переводы страниц (ключ — исходный русский текст) */
  const X = {
    en: {'LIVO — твой мир развлечений':'LIVO — your world of entertainment','Фильмы, игры, занятия, тренировки и челленджи.':'Movies, games, activities, workouts and challenges.','Выбирай. Играй. Живи.':'Choose. Play. Live.','Найди, что посмотреть сегодня':'Find something to watch today','Куда пойти':'Where to go','Идеи для свободного времени':'Ideas for your free time','Испытай себя':'Challenge yourself','Фильмы 2000–2026':'Movies 2000–2026','Все игры →':'All games →','LIVO для Android':'LIVO for Android','Установи приложение — LIVO откроется на весь экран, как обычное приложение.':'Install the app — LIVO opens full screen, like a regular app.','Скачать APK':'Download APK','Открой для себя больше':'Discover more','Подборки, челленджи и идеи для каждого дня.':'Collections, challenges and ideas for every day.','Ищи по названию, жанру или году — результаты обновляются мгновенно':'Search by title, genre or year — results update instantly','Игры разных жанров с 2000 года по настоящее время':'Games of all genres from 2000 to today','Приложение LIVO для Android':'LIVO app for Android','Официальное мобильное приложение сервиса LIVO':'The official mobile app of the LIVO service','Предоставляет полный доступ к каталогу фильмов и сериалов, играм, фитнесу, челленджам, конструктору сборки ПК и другим разделам платформы.':'Gives full access to the catalog of movies and series, games, fitness, challenges, the PC builder and other sections of the platform.','Приложение синхронизируется с вашим аккаунтом, поддерживает тёмную и светлую тему оформления и обеспечивает удобный доступ ко всем функциям сервиса с устройства Android.':'The app syncs with your account, supports dark and light themes and gives convenient access to all features of the service from an Android device.','Для установки скачайте APK-файл и следуйте инструкциям системы.':'To install, download the APK file and follow the system prompts.','Вы уже пользуетесь приложением LIVO.':'You are already using the LIVO app.','Только для Android · файл LIVO.apk':'Android only · file LIVO.apk','Инструкция по установке приложения LIVO':'How to install the LIVO app','Скачайте официальный APK-файл приложения LIVO.':'Download the official LIVO APK file.','На устройстве Android откройте':'On your Android device open','Настройки → Безопасность':'Settings → Security','(или':'(or','Специальный доступ':'Special access',') и разрешите установку из неизвестных источников / установку приложений из этого источника':') and allow installing from unknown sources / installing apps from this source','Откройте скачанный файл и нажмите':'Open the downloaded file and tap','Установить':'Install','После завершения установки запустите приложение LIVO.':'When the installation finishes, launch the LIVO app.','Войдите в существующий аккаунт или зарегистрируйте новый — все данные (избранное, история, настройки) синхронизируются с сайтом.':'Log in to an existing account or create a new one — all data (favorites, history, settings) syncs with the website.','Приложение требует подключения к интернету.':'The app requires an internet connection.','Приложение':'App'},
    de: {'LIVO — твой мир развлечений':'LIVO — deine Welt der Unterhaltung','Фильмы, игры, занятия, тренировки и челленджи.':'Filme, Spiele, Aktivitäten, Workouts und Challenges.','Выбирай. Играй. Живи.':'Wähle. Spiele. Lebe.','Найди, что посмотреть сегодня':'Finde, was du heute schauen kannst','Куда пойти':'Wohin gehen','Идеи для свободного времени':'Ideen für die Freizeit','Испытай себя':'Fordere dich heraus','Фильмы 2000–2026':'Filme 2000–2026','Все игры →':'Alle Spiele →','LIVO для Android':'LIVO für Android','Установи приложение — LIVO откроется на весь экран, как обычное приложение.':'Installiere die App — LIVO öffnet sich im Vollbild wie eine normale App.','Скачать APK':'APK herunterladen','Открой для себя больше':'Entdecke mehr','Подборки, челленджи и идеи для каждого дня.':'Sammlungen, Challenges und Ideen für jeden Tag.','Ищи по названию, жанру или году — результаты обновляются мгновенно':'Suche nach Titel, Genre oder Jahr — die Ergebnisse aktualisieren sich sofort','Игры разных жанров с 2000 года по настоящее время':'Spiele aller Genres von 2000 bis heute','Приложение LIVO для Android':'LIVO-App für Android','Официальное мобильное приложение сервиса LIVO':'Die offizielle mobile App des Dienstes LIVO','Предоставляет полный доступ к каталогу фильмов и сериалов, играм, фитнесу, челленджам, конструктору сборки ПК и другим разделам платформы.':'Bietet vollen Zugriff auf den Katalog mit Filmen und Serien, Spiele, Fitness, Challenges, den PC-Konfigurator und weitere Bereiche der Plattform.','Приложение синхронизируется с вашим аккаунтом, поддерживает тёмную и светлую тему оформления и обеспечивает удобный доступ ко всем функциям сервиса с устройства Android.':'Die App synchronisiert sich mit deinem Konto, unterstützt dunkles und helles Design und bietet auf Android-Geräten bequemen Zugriff auf alle Funktionen des Dienstes.','Для установки скачайте APK-файл и следуйте инструкциям системы.':'Lade zur Installation die APK-Datei herunter und folge den Anweisungen des Systems.','Вы уже пользуетесь приложением LIVO.':'Du nutzt die LIVO-App bereits.','Только для Android · файл LIVO.apk':'Nur für Android · Datei LIVO.apk','Инструкция по установке приложения LIVO':'Anleitung zur Installation der LIVO-App','Скачайте официальный APK-файл приложения LIVO.':'Lade die offizielle APK-Datei der LIVO-App herunter.','На устройстве Android откройте':'Öffne auf deinem Android-Gerät','Настройки → Безопасность':'Einstellungen → Sicherheit','(или':'(oder','Специальный доступ':'Spezieller Zugriff',') и разрешите установку из неизвестных источников / установку приложений из этого источника':') und erlaube die Installation aus unbekannten Quellen / die Installation von Apps aus dieser Quelle','Откройте скачанный файл и нажмите':'Öffne die heruntergeladene Datei und tippe auf','Установить':'Installieren','После завершения установки запустите приложение LIVO.':'Starte nach der Installation die LIVO-App.','Войдите в существующий аккаунт или зарегистрируйте новый — все данные (избранное, история, настройки) синхронизируются с сайтом.':'Melde dich in einem bestehenden Konto an oder registriere ein neues — alle Daten (Favoriten, Verlauf, Einstellungen) werden mit der Website synchronisiert.','Приложение требует подключения к интернету.':'Die App benötigt eine Internetverbindung.'},
    fr: {'LIVO — твой мир развлечений':'LIVO — ton monde du divertissement','Фильмы, игры, занятия, тренировки и челленджи.':'Films, jeux, activités, entraînements et défis.','Выбирай. Играй. Живи.':'Choisis. Joue. Vis.','Найди, что посмотреть сегодня':'Trouve quoi regarder aujourd’hui','Куда пойти':'Où aller','Идеи для свободного времени':'Idées pour le temps libre','Испытай себя':'Mets-toi au défi','Фильмы 2000–2026':'Films 2000–2026','Все игры →':'Tous les jeux →','LIVO для Android':'LIVO pour Android','Установи приложение — LIVO откроется на весь экран, как обычное приложение.':'Installe l’application — LIVO s’ouvre en plein écran, comme une application ordinaire.','Скачать APK':'Télécharger l’APK','Открой для себя больше':'Découvre plus','Подборки, челленджи и идеи для каждого дня.':'Sélections, défis et idées pour chaque jour.','Ищи по названию, жанру или году — результаты обновляются мгновенно':'Cherche par titre, genre ou année — les résultats se mettent à jour instantanément','Игры разных жанров с 2000 года по настоящее время':'Des jeux de tous les genres de 2000 à aujourd’hui','Приложение LIVO для Android':'Application LIVO pour Android','Официальное мобильное приложение сервиса LIVO':'L’application mobile officielle du service LIVO','Предоставляет полный доступ к каталогу фильмов и сериалов, играм, фитнесу, челленджам, конструктору сборки ПК и другим разделам платформы.':'Donne un accès complet au catalogue de films et séries, aux jeux, au fitness, aux défis, au configurateur de PC et aux autres sections de la plateforme.','Приложение синхронизируется с вашим аккаунтом, поддерживает тёмную и светлую тему оформления и обеспечивает удобный доступ ко всем функциям сервиса с устройства Android.':'L’application se synchronise avec votre compte, prend en charge les thèmes sombre et clair et offre un accès pratique à toutes les fonctions du service depuis un appareil Android.','Для установки скачайте APK-файл и следуйте инструкциям системы.':'Pour l’installer, téléchargez le fichier APK et suivez les instructions du système.','Вы уже пользуетесь приложением LIVO.':'Vous utilisez déjà l’application LIVO.','Только для Android · файл LIVO.apk':'Android uniquement · fichier LIVO.apk','Инструкция по установке приложения LIVO':'Comment installer l’application LIVO','Скачайте официальный APK-файл приложения LIVO.':'Téléchargez le fichier APK officiel de l’application LIVO.','На устройстве Android откройте':'Sur votre appareil Android, ouvrez','Настройки → Безопасность':'Paramètres → Sécurité','(или':'(ou','Специальный доступ':'Accès spécial',') и разрешите установку из неизвестных источников / установку приложений из этого источника':') et autorisez l’installation depuis des sources inconnues / l’installation d’applications depuis cette source','Откройте скачанный файл и нажмите':'Ouvrez le fichier téléchargé et appuyez sur','Установить':'Installer','После завершения установки запустите приложение LIVO.':'Une fois l’installation terminée, lancez l’application LIVO.','Войдите в существующий аккаунт или зарегистрируйте новый — все данные (избранное, история, настройки) синхронизируются с сайтом.':'Connectez-vous à un compte existant ou créez-en un nouveau — toutes les données (favoris, historique, paramètres) sont synchronisées avec le site.','Приложение требует подключения к интернету.':'L’application nécessite une connexion internet.'},
    es: {'LIVO — твой мир развлечений':'LIVO — tu mundo del entretenimiento','Фильмы, игры, занятия, тренировки и челленджи.':'Películas, juegos, actividades, entrenamientos y desafíos.','Выбирай. Играй. Живи.':'Elige. Juega. Vive.','Найди, что посмотреть сегодня':'Encuentra qué ver hoy','Куда пойти':'Adónde ir','Идеи для свободного времени':'Ideas para el tiempo libre','Испытай себя':'Ponte a prueba','Фильмы 2000–2026':'Películas 2000–2026','Все игры →':'Todos los juegos →','LIVO для Android':'LIVO para Android','Установи приложение — LIVO откроется на весь экран, как обычное приложение.':'Instala la aplicación: LIVO se abre a pantalla completa, como una app normal.','Скачать APK':'Descargar APK','Открой для себя больше':'Descubre más','Подборки, челленджи и идеи для каждого дня.':'Selecciones, desafíos e ideas para cada día.','Ищи по названию, жанру или году — результаты обновляются мгновенно':'Busca por título, género o año: los resultados se actualizan al instante','Игры разных жанров с 2000 года по настоящее время':'Juegos de todos los géneros desde 2000 hasta hoy','Приложение LIVO для Android':'Aplicación LIVO para Android','Официальное мобильное приложение сервиса LIVO':'La aplicación móvil oficial del servicio LIVO','Предоставляет полный доступ к каталогу фильмов и сериалов, играм, фитнесу, челленджам, конструктору сборки ПК и другим разделам платформы.':'Ofrece acceso completo al catálogo de películas y series, juegos, fitness, desafíos, el configurador de PC y otras secciones de la plataforma.','Приложение синхронизируется с вашим аккаунтом, поддерживает тёмную и светлую тему оформления и обеспечивает удобный доступ ко всем функциям сервиса с устройства Android.':'La aplicación se sincroniza con tu cuenta, admite temas oscuro y claro y ofrece acceso cómodo a todas las funciones del servicio desde un dispositivo Android.','Для установки скачайте APK-файл и следуйте инструкциям системы.':'Para instalarla, descarga el archivo APK y sigue las instrucciones del sistema.','Вы уже пользуетесь приложением LIVO.':'Ya estás usando la aplicación LIVO.','Только для Android · файл LIVO.apk':'Solo para Android · archivo LIVO.apk','Инструкция по установке приложения LIVO':'Cómo instalar la aplicación LIVO','Скачайте официальный APK-файл приложения LIVO.':'Descarga el archivo APK oficial de la aplicación LIVO.','На устройстве Android откройте':'En tu dispositivo Android abre','Настройки → Безопасность':'Ajustes → Seguridad','(или':'(o','Специальный доступ':'Acceso especial',') и разрешите установку из неизвестных источников / установку приложений из этого источника':') y permite la instalación desde fuentes desconocidas / la instalación de aplicaciones desde esta fuente','Откройте скачанный файл и нажмите':'Abre el archivo descargado y pulsa','Установить':'Instalar','После завершения установки запустите приложение LIVO.':'Cuando termine la instalación, abre la aplicación LIVO.','Войдите в существующий аккаунт или зарегистрируйте новый — все данные (избранное, история, настройки) синхронизируются с сайтом.':'Inicia sesión en una cuenta existente o crea una nueva: todos los datos (favoritos, historial, ajustes) se sincronizan con el sitio.','Приложение требует подключения к интернету.':'La aplicación requiere conexión a internet.'},
    it: {'LIVO — твой мир развлечений':'LIVO — il tuo mondo dell’intrattenimento','Фильмы, игры, занятия, тренировки и челленджи.':'Film, giochi, attività, allenamenti e sfide.','Выбирай. Играй. Живи.':'Scegli. Gioca. Vivi.','Найди, что посмотреть сегодня':'Trova cosa guardare oggi','Куда пойти':'Dove andare','Идеи для свободного времени':'Idee per il tempo libero','Испытай себя':'Mettiti alla prova','Фильмы 2000–2026':'Film 2000–2026','Все игры →':'Tutti i giochi →','LIVO для Android':'LIVO per Android','Установи приложение — LIVO откроется на весь экран, как обычное приложение.':'Installa l’app: LIVO si apre a schermo intero, come una normale app.','Скачать APK':'Scarica APK','Открой для себя больше':'Scopri di più','Подборки, челленджи и идеи для каждого дня.':'Raccolte, sfide e idee per ogni giorno.','Ищи по названию, жанру или году — результаты обновляются мгновенно':'Cerca per titolo, genere o anno: i risultati si aggiornano all’istante','Игры разных жанров с 2000 года по настоящее время':'Giochi di tutti i generi dal 2000 a oggi','Приложение LIVO для Android':'App LIVO per Android','Официальное мобильное приложение сервиса LIVO':'L’app mobile ufficiale del servizio LIVO','Предоставляет полный доступ к каталогу фильмов и сериалов, играм, фитнесу, челленджам, конструктору сборки ПК и другим разделам платформы.':'Offre pieno accesso al catalogo di film e serie, giochi, fitness, sfide, al configuratore PC e ad altre sezioni della piattaforma.','Приложение синхронизируется с вашим аккаунтом, поддерживает тёмную и светлую тему оформления и обеспечивает удобный доступ ко всем функциям сервиса с устройства Android.':'L’app si sincronizza con il tuo account, supporta i temi scuro e chiaro e offre un comodo accesso a tutte le funzioni del servizio da un dispositivo Android.','Для установки скачайте APK-файл и следуйте инструкциям системы.':'Per installarla, scarica il file APK e segui le istruzioni del sistema.','Вы уже пользуетесь приложением LIVO.':'Stai già usando l’app LIVO.','Только для Android · файл LIVO.apk':'Solo Android · file LIVO.apk','Инструкция по установке приложения LIVO':'Come installare l’app LIVO','Скачайте официальный APK-файл приложения LIVO.':'Scarica il file APK ufficiale dell’app LIVO.','На устройстве Android откройте':'Sul tuo dispositivo Android apri','Настройки → Безопасность':'Impostazioni → Sicurezza','(или':'(oppure','Специальный доступ':'Accesso speciale',') и разрешите установку из неизвестных источников / установку приложений из этого источника':') e consenti l’installazione da fonti sconosciute / l’installazione di app da questa fonte','Откройте скачанный файл и нажмите':'Apri il file scaricato e tocca','Установить':'Installa','После завершения установки запустите приложение LIVO.':'Al termine dell’installazione, avvia l’app LIVO.','Войдите в существующий аккаунт или зарегистрируйте новый — все данные (избранное, история, настройки) синхронизируются с сайтом.':'Accedi a un account esistente o creane uno nuovo: tutti i dati (preferiti, cronologia, impostazioni) si sincronizzano con il sito.','Приложение требует подключения к интернету.':'L’app richiede una connessione a internet.'},
    uk: {'LIVO — твой мир развлечений':'LIVO — твій світ розваг','Фильмы, игры, занятия, тренировки и челленджи.':'Фільми, ігри, заняття, тренування та челенджі.','Выбирай. Играй. Живи.':'Обирай. Грай. Живи.','Найди, что посмотреть сегодня':'Знайди, що подивитися сьогодні','Куда пойти':'Куди піти','Идеи для свободного времени':'Ідеї для вільного часу','Испытай себя':'Випробуй себе','Фильмы 2000–2026':'Фільми 2000–2026','Все игры →':'Усі ігри →','LIVO для Android':'LIVO для Android','Установи приложение — LIVO откроется на весь экран, как обычное приложение.':'Встанови застосунок — LIVO відкриється на весь екран, як звичайний застосунок.','Скачать APK':'Завантажити APK','Открой для себя больше':'Відкрий для себе більше','Подборки, челленджи и идеи для каждого дня.':'Добірки, челенджі та ідеї на кожен день.','Ищи по названию, жанру или году — результаты обновляются мгновенно':'Шукай за назвою, жанром або роком — результати оновлюються миттєво','Игры разных жанров с 2000 года по настоящее время':'Ігри різних жанрів з 2000 року до сьогодні','Приложение LIVO для Android':'Застосунок LIVO для Android','Официальное мобильное приложение сервиса LIVO':'Офіційний мобільний застосунок сервісу LIVO','Предоставляет полный доступ к каталогу фильмов и сериалов, играм, фитнесу, челленджам, конструктору сборки ПК и другим разделам платформы.':'Надає повний доступ до каталогу фільмів і серіалів, ігор, фітнесу, челенджів, конструктора збірки ПК та інших розділів платформи.','Приложение синхронизируется с вашим аккаунтом, поддерживает тёмную и светлую тему оформления и обеспечивает удобный доступ ко всем функциям сервиса с устройства Android.':'Застосунок синхронізується з вашим акаунтом, підтримує темну та світлу теми оформлення й забезпечує зручний доступ до всіх функцій сервісу з пристрою Android.','Для установки скачайте APK-файл и следуйте инструкциям системы.':'Для встановлення завантажте APK-файл і дотримуйтесь вказівок системи.','Вы уже пользуетесь приложением LIVO.':'Ви вже користуєтеся застосунком LIVO.','Только для Android · файл LIVO.apk':'Лише для Android · файл LIVO.apk','Инструкция по установке приложения LIVO':'Інструкція зі встановлення застосунку LIVO','Скачайте официальный APK-файл приложения LIVO.':'Завантажте офіційний APK-файл застосунку LIVO.','На устройстве Android откройте':'На пристрої Android відкрийте','Настройки → Безопасность':'Налаштування → Безпека','(или':'(або','Специальный доступ':'Спеціальний доступ',') и разрешите установку из неизвестных источников / установку приложений из этого источника':') і дозвольте встановлення з невідомих джерел / встановлення застосунків із цього джерела','Откройте скачанный файл и нажмите':'Відкрийте завантажений файл і натисніть','Установить':'Встановити','После завершения установки запустите приложение LIVO.':'Після завершення встановлення запустіть застосунок LIVO.','Войдите в существующий аккаунт или зарегистрируйте новый — все данные (избранное, история, настройки) синхронизируются с сайтом.':'Увійдіть в існуючий акаунт або зареєструйте новий — усі дані (обране, історія, налаштування) синхронізуються із сайтом.','Приложение требует подключения к интернету.':'Застосунок потребує підключення до інтернету.'},
    pl: {'LIVO — твой мир развлечений':'LIVO — twój świat rozrywki','Фильмы, игры, занятия, тренировки и челленджи.':'Filmy, gry, zajęcia, treningi i wyzwania.','Выбирай. Играй. Живи.':'Wybieraj. Graj. Żyj.','Найди, что посмотреть сегодня':'Znajdź, co obejrzeć dziś','Куда пойти':'Dokąd pójść','Идеи для свободного времени':'Pomysły na wolny czas','Испытай себя':'Sprawdź się','Фильмы 2000–2026':'Filmy 2000–2026','Все игры →':'Wszystkie gry →','LIVO для Android':'LIVO na Androida','Установи приложение — LIVO откроется на весь экран, как обычное приложение.':'Zainstaluj aplikację — LIVO otwiera się na pełnym ekranie jak zwykła aplikacja.','Скачать APK':'Pobierz APK','Открой для себя больше':'Odkryj więcej','Подборки, челленджи и идеи для каждого дня.':'Zestawienia, wyzwania i pomysły na każdy dzień.','Ищи по названию, жанру или году — результаты обновляются мгновенно':'Szukaj według tytułu, gatunku lub roku — wyniki odświeżają się natychmiast','Игры разных жанров с 2000 года по настоящее время':'Gry różnych gatunków od 2000 roku do dziś','Приложение LIVO для Android':'Aplikacja LIVO na Androida','Официальное мобильное приложение сервиса LIVO':'Oficjalna aplikacja mobilna serwisu LIVO','Предоставляет полный доступ к каталогу фильмов и сериалов, играм, фитнесу, челленджам, конструктору сборки ПК и другим разделам платформы.':'Zapewnia pełny dostęp do katalogu filmów i seriali, gier, fitnessu, wyzwań, konfiguratora PC i innych sekcji platformy.','Приложение синхронизируется с вашим аккаунтом, поддерживает тёмную и светлую тему оформления и обеспечивает удобный доступ ко всем функциям сервиса с устройства Android.':'Aplikacja synchronizuje się z Twoim kontem, obsługuje ciemny i jasny motyw oraz zapewnia wygodny dostęp do wszystkich funkcji serwisu na urządzeniu z Androidem.','Для установки скачайте APK-файл и следуйте инструкциям системы.':'Aby zainstalować, pobierz plik APK i postępuj zgodnie z instrukcjami systemu.','Вы уже пользуетесь приложением LIVO.':'Korzystasz już z aplikacji LIVO.','Только для Android · файл LIVO.apk':'Tylko Android · plik LIVO.apk','Инструкция по установке приложения LIVO':'Instrukcja instalacji aplikacji LIVO','Скачайте официальный APK-файл приложения LIVO.':'Pobierz oficjalny plik APK aplikacji LIVO.','На устройстве Android откройте':'Na urządzeniu z Androidem otwórz','Настройки → Безопасность':'Ustawienia → Bezpieczeństwo','(или':'(lub','Специальный доступ':'Dostęp specjalny',') и разрешите установку из неизвестных источников / установку приложений из этого источника':') i zezwól na instalację z nieznanych źródeł / instalację aplikacji z tego źródła','Откройте скачанный файл и нажмите':'Otwórz pobrany plik i naciśnij','Установить':'Zainstaluj','После завершения установки запустите приложение LIVO.':'Po zakończeniu instalacji uruchom aplikację LIVO.','Войдите в существующий аккаунт или зарегистрируйте новый — все данные (избранное, история, настройки) синхронизируются с сайтом.':'Zaloguj się na istniejące konto lub załóż nowe — wszystkie dane (ulubione, historia, ustawienia) synchronizują się ze stroną.','Приложение требует подключения к интернету.':'Aplikacja wymaga połączenia z internetem.'},
    nl: {'LIVO — твой мир развлечений':'LIVO — jouw wereld van entertainment','Фильмы, игры, занятия, тренировки и челленджи.':'Films, games, activiteiten, workouts en uitdagingen.','Выбирай. Играй. Живи.':'Kies. Speel. Leef.','Найди, что посмотреть сегодня':'Vind iets om vandaag te kijken','Куда пойти':'Waar naartoe','Идеи для свободного времени':'Ideeën voor je vrije tijd','Испытай себя':'Daag jezelf uit','Фильмы 2000–2026':'Films 2000–2026','Все игры →':'Alle games →','LIVO для Android':'LIVO voor Android','Установи приложение — LIVO откроется на весь экран, как обычное приложение.':'Installeer de app — LIVO opent op volledig scherm, zoals een gewone app.','Скачать APK':'APK downloaden','Открой для себя больше':'Ontdek meer','Подборки, челленджи и идеи для каждого дня.':'Selecties, uitdagingen en ideeën voor elke dag.','Ищи по названию, жанру или году — результаты обновляются мгновенно':'Zoek op titel, genre of jaar — de resultaten worden direct bijgewerkt','Игры разных жанров с 2000 года по настоящее время':'Games van alle genres van 2000 tot nu','Приложение LIVO для Android':'LIVO-app voor Android','Официальное мобильное приложение сервиса LIVO':'De officiële mobiele app van de LIVO-dienst','Предоставляет полный доступ к каталогу фильмов и сериалов, играм, фитнесу, челленджам, конструктору сборки ПК и другим разделам платформы.':'Geeft volledige toegang tot de catalogus met films en series, games, fitness, uitdagingen, de pc-samensteller en andere onderdelen van het platform.','Приложение синхронизируется с вашим аккаунтом, поддерживает тёмную и светлую тему оформления и обеспечивает удобный доступ ко всем функциям сервиса с устройства Android.':'De app synchroniseert met je account, ondersteunt een donker en licht thema en biedt handige toegang tot alle functies van de dienst vanaf een Android-apparaat.','Для установки скачайте APK-файл и следуйте инструкциям системы.':'Download het APK-bestand om te installeren en volg de instructies van het systeem.','Вы уже пользуетесь приложением LIVO.':'Je gebruikt de LIVO-app al.','Только для Android · файл LIVO.apk':'Alleen voor Android · bestand LIVO.apk','Инструкция по установке приложения LIVO':'Zo installeer je de LIVO-app','Скачайте официальный APK-файл приложения LIVO.':'Download het officiële APK-bestand van de LIVO-app.','На устройстве Android откройте':'Open op je Android-apparaat','Настройки → Безопасность':'Instellingen → Beveiliging','(или':'(of','Специальный доступ':'Speciale toegang',') и разрешите установку из неизвестных источников / установку приложений из этого источника':') en sta installatie uit onbekende bronnen / het installeren van apps uit deze bron toe','Откройте скачанный файл и нажмите':'Open het gedownloade bestand en tik op','Установить':'Installeren','После завершения установки запустите приложение LIVO.':'Start de LIVO-app zodra de installatie klaar is.','Войдите в существующий аккаунт или зарегистрируйте новый — все данные (избранное, история, настройки) синхронизируются с сайтом.':'Log in op een bestaand account of maak een nieuw account aan — alle gegevens (favorieten, geschiedenis, instellingen) worden met de website gesynchroniseerd.','Приложение требует подключения к интернету.':'De app heeft een internetverbinding nodig.'}
  };
  Object.keys(X).forEach((l) => { T[l] = Object.assign(T[l] || {}, X[l]); });
  const X2 = {"en": {"Друзья": "Friends", "Найди друзей по имени пользователя и смотри их статистику.": "Find friends by username and see their stats.", "Имя пользователя…": "Username…", "Искать": "Search", "Результаты поиска": "Search results", "Мои друзья": "My friends", "Никого не найдено": "No one found", "Введи минимум 2 символа.": "Enter at least 2 characters.", "Пока нет друзей. Найди кого-нибудь по имени пользователя.": "No friends yet. Find someone by username.", "Добавить в друзья": "Add friend", "Убрать из друзей": "Remove friend", "В друзьях": "Friends", "Войди в аккаунт, чтобы добавлять друзей.": "Log in to add friends.", "Статистика скрыта": "Stats hidden", "Это ваш профиль": "This is your profile", "Редактировать профиль": "Edit profile", "Фильмов в избранном": "Movies in favorites", "Игр в избранном": "Games in favorites", "Просмотрено фильмов": "Movies watched", "Друзей": "Friends", "С нами с": "Member since", "Любимый жанр": "Favorite genre", "Статистика": "Statistics", "Избранные фильмы": "Favorite movies", "Избранные игры": "Favorite games", "Пользователь скрыл свою статистику и избранное.": "This user has hidden their stats and favorites.", "Пока ничего нет.": "Nothing here yet.", "К поиску друзей": "Back to friend search", "Показывать мою статистику и избранное другим пользователям": "Show my stats and favorites to other users", "Мой публичный профиль": "My public profile", "Добавлено в друзья ✅": "Added to friends ✅", "Убрано из друзей.": "Removed from friends.", "Слишком много запросов. Подожди минуту.": "Too many requests. Wait a minute.", "Не удалось выполнить поиск. Проверь соединение.": "Search failed. Check your connection.", "Не удалось добавить пользователя.": "Could not add this user.", "в избранном": "in favorites", "просмотрено": "watched"}, "de": {"Друзья": "Freunde", "Найди друзей по имени пользователя и смотри их статистику.": "Finde Freunde per Benutzername und sieh ihre Statistiken.", "Имя пользователя…": "Benutzername…", "Искать": "Suchen", "Результаты поиска": "Suchergebnisse", "Мои друзья": "Meine Freunde", "Никого не найдено": "Niemand gefunden", "Введи минимум 2 символа.": "Gib mindestens 2 Zeichen ein.", "Пока нет друзей. Найди кого-нибудь по имени пользователя.": "Noch keine Freunde. Finde jemanden per Benutzername.", "Добавить в друзья": "Freund hinzufügen", "Убрать из друзей": "Freund entfernen", "В друзьях": "Befreundet", "Войди в аккаунт, чтобы добавлять друзей.": "Melde dich an, um Freunde hinzuzufügen.", "Статистика скрыта": "Statistik verborgen", "Это ваш профиль": "Das ist dein Profil", "Редактировать профиль": "Profil bearbeiten", "Фильмов в избранном": "Filme in Favoriten", "Игр в избранном": "Spiele in Favoriten", "Просмотрено фильмов": "Gesehene Filme", "Друзей": "Freunde", "С нами с": "Dabei seit", "Любимый жанр": "Lieblingsgenre", "Статистика": "Statistik", "Избранные фильмы": "Lieblingsfilme", "Избранные игры": "Lieblingsspiele", "Пользователь скрыл свою статистику и избранное.": "Dieser Nutzer hat seine Statistik und Favoriten verborgen.", "Пока ничего нет.": "Noch nichts da.", "К поиску друзей": "Zurück zur Freundessuche", "Показывать мою статистику и избранное другим пользователям": "Meine Statistik und Favoriten für andere sichtbar machen", "Мой публичный профиль": "Mein öffentliches Profil", "Добавлено в друзья ✅": "Zu Freunden hinzugefügt ✅", "Убрано из друзей.": "Aus Freunden entfernt.", "Слишком много запросов. Подожди минуту.": "Zu viele Anfragen. Warte eine Minute.", "Не удалось выполнить поиск. Проверь соединение.": "Suche fehlgeschlagen. Prüfe deine Verbindung.", "Не удалось добавить пользователя.": "Nutzer konnte nicht hinzugefügt werden.", "в избранном": "in Favoriten", "просмотрено": "angesehen"}, "fr": {"Друзья": "Amis", "Найди друзей по имени пользователя и смотри их статистику.": "Trouve des amis par nom d’utilisateur et consulte leurs statistiques.", "Имя пользователя…": "Nom d’utilisateur…", "Искать": "Rechercher", "Результаты поиска": "Résultats de recherche", "Мои друзья": "Mes amis", "Никого не найдено": "Personne trouvé", "Введи минимум 2 символа.": "Saisis au moins 2 caractères.", "Пока нет друзей. Найди кого-нибудь по имени пользователя.": "Pas encore d’amis. Trouve quelqu’un par nom d’utilisateur.", "Добавить в друзья": "Ajouter en ami", "Убрать из друзей": "Retirer des amis", "В друзьях": "Ami", "Войди в аккаунт, чтобы добавлять друзей.": "Connecte-toi pour ajouter des amis.", "Статистика скрыта": "Statistiques masquées", "Это ваш профиль": "C’est ton profil", "Редактировать профиль": "Modifier le profil", "Фильмов в избранном": "Films en favoris", "Игр в избранном": "Jeux en favoris", "Просмотрено фильмов": "Films vus", "Друзей": "Amis", "С нами с": "Membre depuis", "Любимый жанр": "Genre préféré", "Статистика": "Statistiques", "Избранные фильмы": "Films favoris", "Избранные игры": "Jeux favoris", "Пользователь скрыл свою статистику и избранное.": "Cet utilisateur a masqué ses statistiques et ses favoris.", "Пока ничего нет.": "Rien pour le moment.", "К поиску друзей": "Retour à la recherche d’amis", "Показывать мою статистику и избранное другим пользователям": "Afficher mes statistiques et favoris aux autres utilisateurs", "Мой публичный профиль": "Mon profil public", "Добавлено в друзья ✅": "Ajouté aux amis ✅", "Убрано из друзей.": "Retiré des amis.", "Слишком много запросов. Подожди минуту.": "Trop de requêtes. Attends une minute.", "Не удалось выполнить поиск. Проверь соединение.": "Échec de la recherche. Vérifie ta connexion.", "Не удалось добавить пользователя.": "Impossible d’ajouter cet utilisateur.", "в избранном": "en favoris", "просмотрено": "vus"}, "es": {"Друзья": "Amigos", "Найди друзей по имени пользователя и смотри их статистику.": "Encuentra amigos por nombre de usuario y mira sus estadísticas.", "Имя пользователя…": "Nombre de usuario…", "Искать": "Buscar", "Результаты поиска": "Resultados de búsqueda", "Мои друзья": "Mis amigos", "Никого не найдено": "No se encontró a nadie", "Введи минимум 2 символа.": "Introduce al menos 2 caracteres.", "Пока нет друзей. Найди кого-нибудь по имени пользователя.": "Aún no tienes amigos. Busca a alguien por nombre de usuario.", "Добавить в друзья": "Añadir amigo", "Убрать из друзей": "Quitar amigo", "В друзьях": "Amigo", "Войди в аккаунт, чтобы добавлять друзей.": "Inicia sesión para añadir amigos.", "Статистика скрыта": "Estadísticas ocultas", "Это ваш профиль": "Este es tu perfil", "Редактировать профиль": "Editar perfil", "Фильмов в избранном": "Películas en favoritos", "Игр в избранном": "Juegos en favoritos", "Просмотрено фильмов": "Películas vistas", "Друзей": "Amigos", "С нами с": "Miembro desde", "Любимый жанр": "Género favorito", "Статистика": "Estadísticas", "Избранные фильмы": "Películas favoritas", "Избранные игры": "Juegos favoritos", "Пользователь скрыл свою статистику и избранное.": "Este usuario ha ocultado sus estadísticas y favoritos.", "Пока ничего нет.": "Aún no hay nada.", "К поиску друзей": "Volver a buscar amigos", "Показывать мою статистику и избранное другим пользователям": "Mostrar mis estadísticas y favoritos a otros usuarios", "Мой публичный профиль": "Mi perfil público", "Добавлено в друзья ✅": "Añadido a amigos ✅", "Убрано из друзей.": "Quitado de amigos.", "Слишком много запросов. Подожди минуту.": "Demasiadas solicitudes. Espera un minuto.", "Не удалось выполнить поиск. Проверь соединение.": "Error en la búsqueda. Revisa tu conexión.", "Не удалось добавить пользователя.": "No se pudo añadir al usuario.", "в избранном": "en favoritos", "просмотрено": "vistas"}, "it": {"Друзья": "Amici", "Найди друзей по имени пользователя и смотри их статистику.": "Trova amici tramite nome utente e guarda le loro statistiche.", "Имя пользователя…": "Nome utente…", "Искать": "Cerca", "Результаты поиска": "Risultati della ricerca", "Мои друзья": "I miei amici", "Никого не найдено": "Nessuno trovato", "Введи минимум 2 символа.": "Inserisci almeno 2 caratteri.", "Пока нет друзей. Найди кого-нибудь по имени пользователя.": "Ancora nessun amico. Trova qualcuno tramite nome utente.", "Добавить в друзья": "Aggiungi amico", "Убрать из друзей": "Rimuovi amico", "В друзьях": "Amico", "Войди в аккаунт, чтобы добавлять друзей.": "Accedi per aggiungere amici.", "Статистика скрыта": "Statistiche nascoste", "Это ваш профиль": "Questo è il tuo profilo", "Редактировать профиль": "Modifica profilo", "Фильмов в избранном": "Film nei preferiti", "Игр в избранном": "Giochi nei preferiti", "Просмотрено фильмов": "Film visti", "Друзей": "Amici", "С нами с": "Iscritto dal", "Любимый жанр": "Genere preferito", "Статистика": "Statistiche", "Избранные фильмы": "Film preferiti", "Избранные игры": "Giochi preferiti", "Пользователь скрыл свою статистику и избранное.": "Questo utente ha nascosto statistiche e preferiti.", "Пока ничего нет.": "Ancora niente.", "К поиску друзей": "Torna alla ricerca amici", "Показывать мою статистику и избранное другим пользователям": "Mostra le mie statistiche e i preferiti agli altri utenti", "Мой публичный профиль": "Il mio profilo pubblico", "Добавлено в друзья ✅": "Aggiunto agli amici ✅", "Убрано из друзей.": "Rimosso dagli amici.", "Слишком много запросов. Подожди минуту.": "Troppe richieste. Attendi un minuto.", "Не удалось выполнить поиск. Проверь соединение.": "Ricerca non riuscita. Controlla la connessione.", "Не удалось добавить пользователя.": "Impossibile aggiungere l’utente.", "в избранном": "nei preferiti", "просмотрено": "visti"}, "uk": {"Друзья": "Друзі", "Найди друзей по имени пользователя и смотри их статистику.": "Знайди друзів за іменем користувача й дивись їхню статистику.", "Имя пользователя…": "Ім’я користувача…", "Искать": "Шукати", "Результаты поиска": "Результати пошуку", "Мои друзья": "Мої друзі", "Никого не найдено": "Нікого не знайдено", "Введи минимум 2 символа.": "Введи щонайменше 2 символи.", "Пока нет друзей. Найди кого-нибудь по имени пользователя.": "Поки немає друзів. Знайди когось за іменем користувача.", "Добавить в друзья": "Додати в друзі", "Убрать из друзей": "Прибрати з друзів", "В друзьях": "У друзях", "Войди в аккаунт, чтобы добавлять друзей.": "Увійди в акаунт, щоб додавати друзів.", "Статистика скрыта": "Статистику приховано", "Это ваш профиль": "Це твій профіль", "Редактировать профиль": "Редагувати профіль", "Фильмов в избранном": "Фільмів в обраному", "Игр в избранном": "Ігор в обраному", "Просмотрено фильмов": "Переглянуто фільмів", "Друзей": "Друзів", "С нами с": "З нами з", "Любимый жанр": "Улюблений жанр", "Статистика": "Статистика", "Избранные фильмы": "Обрані фільми", "Избранные игры": "Обрані ігри", "Пользователь скрыл свою статистику и избранное.": "Користувач приховав свою статистику й обране.", "Пока ничего нет.": "Поки нічого немає.", "К поиску друзей": "До пошуку друзів", "Показывать мою статистику и избранное другим пользователям": "Показувати мою статистику й обране іншим користувачам", "Мой публичный профиль": "Мій публічний профіль", "Добавлено в друзья ✅": "Додано в друзі ✅", "Убрано из друзей.": "Прибрано з друзів.", "Слишком много запросов. Подожди минуту.": "Забагато запитів. Зачекай хвилину.", "Не удалось выполнить поиск. Проверь соединение.": "Не вдалося виконати пошук. Перевір з’єднання.", "Не удалось добавить пользователя.": "Не вдалося додати користувача.", "в избранном": "в обраному", "просмотрено": "переглянуто"}, "pl": {"Друзья": "Znajomi", "Найди друзей по имени пользователя и смотри их статистику.": "Znajdź znajomych po nazwie użytkownika i zobacz ich statystyki.", "Имя пользователя…": "Nazwa użytkownika…", "Искать": "Szukaj", "Результаты поиска": "Wyniki wyszukiwania", "Мои друзья": "Moi znajomi", "Никого не найдено": "Nikogo nie znaleziono", "Введи минимум 2 символа.": "Wpisz co najmniej 2 znaki.", "Пока нет друзей. Найди кого-нибудь по имени пользователя.": "Jeszcze nie masz znajomych. Znajdź kogoś po nazwie użytkownika.", "Добавить в друзья": "Dodaj do znajomych", "Убрать из друзей": "Usuń ze znajomych", "В друзьях": "Znajomy", "Войди в аккаунт, чтобы добавлять друзей.": "Zaloguj się, aby dodawać znajomych.", "Статистика скрыта": "Statystyki ukryte", "Это ваш профиль": "To jest Twój profil", "Редактировать профиль": "Edytuj profil", "Фильмов в избранном": "Filmy w ulubionych", "Игр в избранном": "Gry w ulubionych", "Просмотрено фильмов": "Obejrzane filmy", "Друзей": "Znajomi", "С нами с": "Z nami od", "Любимый жанр": "Ulubiony gatunek", "Статистика": "Statystyki", "Избранные фильмы": "Ulubione filmy", "Избранные игры": "Ulubione gry", "Пользователь скрыл свою статистику и избранное.": "Ten użytkownik ukrył swoje statystyki i ulubione.", "Пока ничего нет.": "Na razie nic nie ma.", "К поиску друзей": "Wróć do wyszukiwania znajomych", "Показывать мою статистику и избранное другим пользователям": "Pokazuj moje statystyki i ulubione innym użytkownikom", "Мой публичный профиль": "Mój profil publiczny", "Добавлено в друзья ✅": "Dodano do znajomych ✅", "Убрано из друзей.": "Usunięto ze znajomych.", "Слишком много запросов. Подожди минуту.": "Zbyt wiele żądań. Poczekaj minutę.", "Не удалось выполнить поиск. Проверь соединение.": "Wyszukiwanie nie powiodło się. Sprawdź połączenie.", "Не удалось добавить пользователя.": "Nie udało się dodać użytkownika.", "в избранном": "w ulubionych", "просмотрено": "obejrzane"}, "nl": {"Друзья": "Vrienden", "Найди друзей по имени пользователя и смотри их статистику.": "Zoek vrienden op gebruikersnaam en bekijk hun statistieken.", "Имя пользователя…": "Gebruikersnaam…", "Искать": "Zoeken", "Результаты поиска": "Zoekresultaten", "Мои друзья": "Mijn vrienden", "Никого не найдено": "Niemand gevonden", "Введи минимум 2 символа.": "Voer minstens 2 tekens in.", "Пока нет друзей. Найди кого-нибудь по имени пользователя.": "Nog geen vrienden. Zoek iemand op gebruikersnaam.", "Добавить в друзья": "Vriend toevoegen", "Убрать из друзей": "Vriend verwijderen", "В друзьях": "Vriend", "Войди в аккаунт, чтобы добавлять друзей.": "Log in om vrienden toe te voegen.", "Статистика скрыта": "Statistieken verborgen", "Это ваш профиль": "Dit is jouw profiel", "Редактировать профиль": "Profiel bewerken", "Фильмов в избранном": "Films in favorieten", "Игр в избранном": "Games in favorieten", "Просмотрено фильмов": "Bekeken films", "Друзей": "Vrienden", "С нами с": "Lid sinds", "Любимый жанр": "Favoriet genre", "Статистика": "Statistieken", "Избранные фильмы": "Favoriete films", "Избранные игры": "Favoriete games", "Пользователь скрыл свою статистику и избранное.": "Deze gebruiker heeft statistieken en favorieten verborgen.", "Пока ничего нет.": "Nog niets hier.", "К поиску друзей": "Terug naar vrienden zoeken", "Показывать мою статистику и избранное другим пользователям": "Mijn statistieken en favorieten tonen aan andere gebruikers", "Мой публичный профиль": "Mijn openbare profiel", "Добавлено в друзья ✅": "Toegevoegd aan vrienden ✅", "Убрано из друзей.": "Verwijderd uit vrienden.", "Слишком много запросов. Подожди минуту.": "Te veel verzoeken. Wacht een minuut.", "Не удалось выполнить поиск. Проверь соединение.": "Zoeken mislukt. Controleer je verbinding.", "Не удалось добавить пользователя.": "Gebruiker kon niet worden toegevoegd.", "в избранном": "in favorieten", "просмотрено": "bekeken"}};
  Object.keys(X2).forEach((l) => { T[l] = Object.assign(T[l] || {}, X2[l]); });
  const WORDS = { en:['movies','games','Found'], de:['Filme','Spiele','Gefunden'], fr:['films','jeux','Trouvé'], es:['películas','juegos','Encontrado'],
                  it:['film','giochi','Trovati'], uk:['фільмів','ігор','Знайдено'], pl:['filmów','gier','Znaleziono'], nl:['films','games','Gevonden'] };

  function getLang() {
    let v = null;
    try { v = localStorage.getItem(LANG_KEY); } catch (e) {}
    if (!LANGS.includes(v)) v = (navigator.language || 'ru').slice(0,2).toLowerCase();
    return LANGS.includes(v) ? v : 'ru';
  }
  function tr(s, lang) { return (T[lang] && T[lang][s]) || (T.ru[s]) || s; }

  // Переводит строку, всегда исходя из ОРИГИНАЛА (русского). Эмодзи/стрелки по краям сохраняются.
  function translateString(raw, lang) {
    if (lang === 'ru') return raw;
    const d = T[lang]; if (!d) return raw;
    const lead = raw.match(/^\s*/)[0], trail = raw.match(/\s*$/)[0], key = raw.trim();
    if (!key) return raw;
    if (d[key]) return lead + d[key] + trail;
    let m = key.match(/^(\d+)\s+(фильм|фильма|фильмов|игра|игры|игр)$/);
    if (m && WORDS[lang]) return lead + m[1] + ' ' + WORDS[lang][/^фильм/.test(m[2]) ? 0 : 1] + trail;
    m = key.match(/^Найдено:\s*(\d+)$/);
    if (m && WORDS[lang]) return lead + WORDS[lang][2] + ': ' + m[1] + trail;
    m = key.match(/^([^\p{L}\p{N}]*)([\s\S]*?)([^\p{L}\p{N}]*)$/u);
    if (m && m[2] && d[m[2]]) return lead + m[1] + d[m[2]] + m[3] + trail;
    return raw;
  }

  const textStore = new WeakMap();
  function applyText(node, lang) {
    let rec = textStore.get(node);
    if (!rec || node.nodeValue !== rec.out) rec = { orig: node.nodeValue, out: node.nodeValue };
    const out = translateString(rec.orig, lang);
    rec.out = out; textStore.set(node, rec);
    if (node.nodeValue !== out) node.nodeValue = out;
  }
  const ATTRS = ['placeholder', 'aria-label', 'title'];
  function applyAttrs(el, lang) {
    ATTRS.forEach((a) => {
      if (!el.hasAttribute(a)) return;
      const cur = el.getAttribute(a);
      el._i18n = el._i18n || {};
      let rec = el._i18n[a];
      if (!rec || cur !== rec.out) rec = { orig: cur, out: cur };
      const out = translateString(rec.orig, lang);
      rec.out = out; el._i18n[a] = rec;
      if (cur !== out) el.setAttribute(a, out);
    });
  }

  let observer = null;
  function translatePage(lang) {
    if (!LANGS.includes(lang)) lang = 'ru';
    if (observer) observer.disconnect();
    document.documentElement.lang = lang;
    $$('[data-language]').forEach((s) => (s.value = lang));
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach((node) => {
      if (!node.nodeValue.trim() || node.parentElement.closest('script,style,select')) return;
      applyText(node, lang);
    });
    $$('[placeholder],[aria-label],[title]').forEach((el) => applyAttrs(el, lang));
    $$('[data-i18n]').forEach((el) => { el.textContent = tr(el.dataset.i18n, lang); });
    if (observer) observer.observe(document.body, { childList: true, subtree: true, characterData: true });
  }

  function setLang(lang) {
    if (!LANGS.includes(lang)) lang = 'ru';
    try { localStorage.setItem(LANG_KEY, lang); } catch (e) {}
    translatePage(lang);
    window.dispatchEvent(new CustomEvent('livo:language', { detail: lang }));
  }
  const current = getLang();
  document.documentElement.lang = current;
  document.addEventListener('DOMContentLoaded', () => {
    $$('[data-language]').forEach((el) => el.addEventListener('change', (e) => setLang(e.target.value)));
    // динамический контент (каталог, подсказки, уведомления) переводим по мере появления
    let queued = false;
    observer = new MutationObserver(() => {
      if (queued) return; queued = true;
      requestAnimationFrame(() => { queued = false; translatePage(getLang()); });
    });
    translatePage(current);
  });
  window.LIVO = window.LIVO || {};
  window.LIVO.translate = translatePage;
  window.LIVO.setLanguage = setLang;
  window.LIVO.getLanguage = getLang;
})();
