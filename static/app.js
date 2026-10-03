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
    const poster = `<div class="poster-ph" data-poster-title="${esc(it.title)}" data-poster-kind="${kind}" style="--h:${h}">
      <span class="poster-loading">Загрузка…</span><span class="ph-emoji" aria-hidden="true">${em}</span><span class="ph-year">${it.year}</span>
    </div>`;
    if (kind === 'movie') return `<div class="card poster-card movie-card reveal">${fav}
      <a class="card-main" href="/movies/${it.id}">${poster}
      <b>${esc(it.title)}</b><span>${esc(it.genre)}</span>${it.rating && it.rating !== '—' ? `<small class="rating">★ ${esc(it.rating)}</small>` : ''}</a></div>`;
    return `<div class="card poster-card game-card reveal">${fav}<div class="card-main">${poster}
      <b>${esc(it.title)}</b><span>${esc(it.genre)}</span><small>${esc(it.platform)}</small></div></div>`;
  }
  /* ---------- Постеры фильмов и игр ---------- */
  const POSTER_CACHE_KEY = 'livo-poster-cache-v1';
  let POSTER_CACHE = {};
  try { POSTER_CACHE = JSON.parse(localStorage.getItem(POSTER_CACHE_KEY) || '{}'); } catch (e) {}

  function savePosterCache() {
    try { localStorage.setItem(POSTER_CACHE_KEY, JSON.stringify(POSTER_CACHE)); } catch (e) {}
  }

  async function findPoster(title) {
    const key = String(title).trim().toLowerCase();
    if (Object.prototype.hasOwnProperty.call(POSTER_CACHE, key)) return POSTER_CACHE[key];

    const url = 'https://en.wikipedia.org/w/api.php?action=query&generator=search&gsrsearch=' +
      encodeURIComponent(title) +
      '&gsrnamespace=0&gsrlimit=1&prop=pageimages&piprop=thumbnail&pithumbsize=700&format=json&origin=*';
    try {
      const r = await fetch(url);
      if (!r.ok) throw new Error('poster request failed');
      const j = await r.json();
      const pages = j.query && j.query.pages ? Object.values(j.query.pages) : [];
      const image = pages[0] && pages[0].thumbnail && pages[0].thumbnail.source;
      POSTER_CACHE[key] = image || '';
      savePosterCache();
      return image || '';
    } catch (e) {
      POSTER_CACHE[key] = '';
      return '';
    }
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
      findPoster(title).then(src => applyPoster(el, src));
    });
  }, { rootMargin: '180px' }) : null;

  async function loadPosters(scope = document) {
    const els = $$('.poster-ph[data-poster-title]:not([data-poster-watched])', scope);
    els.forEach(el => {
      el.dataset.posterWatched = '1';
      if (posterIO) posterIO.observe(el);
      else findPoster(el.dataset.posterTitle).then(src => applyPoster(el, src));
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

  function getLang() {
    let v = null;
    try { v = localStorage.getItem(LANG_KEY); } catch (e) {}
    if (!LANGS.includes(v)) v = (navigator.language || 'ru').slice(0,2).toLowerCase();
    return LANGS.includes(v) ? v : 'ru';
  }
  function tr(s, lang) { return (T[lang] && T[lang][s]) || (T.ru[s]) || s; }
  function translatePage(lang) {
    const dict = T[lang] || T.ru;
    document.documentElement.lang = lang;
    $$('[data-language]').forEach(s => s.value = lang);
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(node => {
      if (!node.nodeValue.trim() || node.parentElement.closest('script,style,select option')) return;
      const raw = node.nodeValue;
      const lead = raw.match(/^\s*/)[0], trail = raw.match(/\s*$/)[0], key = raw.trim();
      if (dict[key] || T.ru[key]) node.nodeValue = lead + tr(key, lang) + trail;
    });
    $$('input[placeholder],textarea[placeholder]').forEach(el => {
      const key = el.getAttribute('placeholder'); if (key && (dict[key] || T.ru[key])) el.setAttribute('placeholder', tr(key, lang));
    });
    $$('[data-i18n]').forEach(el => { const key = el.dataset.i18n; el.textContent = tr(key, lang); });
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
    $$('[data-language]').forEach(el => el.addEventListener('change', e => setLang(e.target.value)));
    translatePage(current);
  });
  window.LIVO = window.LIVO || {};
  window.LIVO.translate = translatePage;
  window.LIVO.setLanguage = setLang;
  window.LIVO.getLanguage = getLang;
})();
