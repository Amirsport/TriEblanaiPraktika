'use strict';

const PANEL_STATE_KEY = 'greenhouse.state.v1';
const CONN_KEY = 'greenhouse.games.conn.v1';
const AUTH_KEY = 'greenhouse.auth.v1';
const THEME_KEY = 'greenhouse.games.theme';
const GAME_KEY = 'greenhouse.games.draft.v1';

const DRAFT = '/api/games/draft';
const DEFAULT_GAME = 'valorant';
const REQUEST_TIMEOUT_MS = 10000;
const POLL_MS = 1500;

/* Страницы отдельных игр («13-0» по Valorant и «4-0» по Rocket League)
   задают свою игру до подключения этого скрипта: window.DRAFT_GAME. Тогда
   страница играет только в неё, а выбора игры в лобби нет. На странице
   драфтов переменной нет — там игра выбирается вручную и запоминается. */
const PRESET_GAME = String(window.DRAFT_GAME || '').trim();

const $ = (selector) => document.querySelector(selector);

let apiBase = '';
let auth = { token: '', user: null };
let catalog = [];                // игры из /api/games/draft/games
let gameKey = '';                // выбранная игра
let game = null;                 // её правила и подписи (game_block)
let info = null;                 // /status: составы, эпохи, сложности, стадии
let run = null;                  // состояние текущего прогона
let journal = [];
let journalScope = 'mine';
let pick = { difficulty: 'hard', era: 'legacy', assign: 'auto' };
let pendingPlayer = '';          // игрок, которому выбираем роль в ручном режиме
let busy = false;
let poller = 0;

/* Адрес игры собирается из выбранного ключа: /api/games/draft/<game>. */
function gamePath() {
  return DRAFT + '/' + gameKey;
}

/* ------------------------------- утилиты -------------------------------- */

function escapeHtml(text) {
  return String(text == null ? '' : text).replace(/[&<>"']/g, (char) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]
  ));
}

const cap = (text) => {
  const value = String(text == null ? '' : text);
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : value;
};

function toast(message, kind) {
  const box = $('#toasts');
  const node = document.createElement('div');
  node.className = 'toast' + (kind ? ' ' + kind : '');
  node.textContent = message;
  box.appendChild(node);
  setTimeout(() => {
    node.classList.add('out');
    setTimeout(() => node.remove(), 320);
  }, 4200);
}

function readJson(key) {
  try {
    const value = JSON.parse(localStorage.getItem(key) || 'null');
    return value && typeof value === 'object' ? value : null;
  } catch (error) {
    return null;
  }
}

function writeJson(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch (error) {
    return false;
  }
}

function show(selector, visible) {
  const node = $(selector);
  if (node) node.hidden = !visible;
}

const num = (value) => (Math.round(Number(value || 0) * 10) / 10).toString();

/* ------------------------------ сеть ------------------------------------ */

const root = () => (apiBase || '').replace(/\/+$/, '');

async function api(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const headers = { 'Content-Type': 'application/json' };
  if (auth.token) headers.Authorization = 'Bearer ' + auth.token;
  try {
    const response = await fetch(root() + path, {
      method: options.method || 'GET',
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
      signal: controller.signal,
      cache: 'no-store'
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(data.error || ('Сервер ответил HTTP ' + response.status));
      error.status = response.status;
      throw error;
    }
    return data;
  } finally {
    clearTimeout(timer);
  }
}

/* Что показать игроку: 429 — не ошибка, а просьба подождать минуту. */
function failMessage(error) {
  if (error && error.status === 429) return 'Слишком много действий, подождите минуту';
  if (error && error.status === 401) return 'Требуется вход в аккаунт';
  return (error && error.message) || 'Не получилось';
}

/* Прогон принадлежит аккаунту: если вход истёк, возвращаем экран входа. */
function sessionExpired(error) {
  if (!error || error.status !== 401) return false;
  auth = { token: '', user: null };
  saveAuth();
  run = null;
  journal = [];
  pendingPlayer = '';
  stopPolling();
  hideAll();
  showAuth('login');
  toast('Сессия истекла — войдите заново', 'err');
  return true;
}

function setConnection(kind, text) {
  const pill = $('#conn-pill');
  pill.classList.toggle('online', kind === 'online');
  pill.classList.toggle('err', kind === 'err');
  $('#conn-text').textContent = text;
  const badge = $('#server-badge');
  if (badge) badge.textContent = text;
}

/* Адрес сервера: свой сохранённый, иначе из настроек панели теплицы. */
function storedConnection() {
  const own = readJson(CONN_KEY) || {};
  return {
    apiBase: String(own.apiBase || '').trim(),
    apiToken: String(own.apiToken || '').trim()
  };
}

function panelConnection() {
  const panel = readJson(PANEL_STATE_KEY) || {};
  return {
    apiBase: String(panel.apiBase || '').trim(),
    apiToken: String(panel.apiToken || '').trim()
  };
}

const trimBase = (value) => String(value || '').trim().replace(/\/+$/, '');

function apiCandidates() {
  const fromLink = trimBase(new URLSearchParams(location.search).get('srv'));
  if (fromLink) return { fixed: true, list: [fromLink] };
  const list = [];
  [storedConnection().apiBase, panelConnection().apiBase].forEach((value) => {
    const item = trimBase(value);
    if (item && list.indexOf(item) < 0) list.push(item);
  });
  return { fixed: false, list };
}

/* Короткая проверка адреса: 401 тоже значит «сервер жив, он закрыт ключом». */
async function pingServer(base) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 2500);
  try {
    const response = await fetch(base + '/api/health', {
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      cache: 'no-store'
    });
    return response.ok || response.status === 401;
  } catch (error) {
    return false;
  } finally {
    clearTimeout(timer);
  }
}

/* Адрес и ключ панели, опубликованные на сайте при выгрузке: у туннеля
   меняется поддомен, а этот файл обновляет серверная сторона. */
let publishedKey = '';
async function publishedApiBase() {
  if (location.protocol !== 'http:' && location.protocol !== 'https:') return '';
  try {
    const response = await fetch('../api-address.json', { cache: 'no-store' });
    if (!response.ok) return '';
    const data = await response.json();
    publishedKey = String((data && data.apiKey) || '').trim();
    return trimBase(data && data.apiBase);
  } catch (error) {
    return '';
  }
}

/* Сохранённый адрес мог устареть: пробуем по очереди всё, что знаем. */
async function resolveApiBase() {
  const { fixed, list } = apiCandidates();
  if (fixed) {
    apiBase = list[0];
    rememberServer(apiBase);
    return apiBase;
  }
  const stored = storedConnection().apiBase;
  const published = publishedApiBase();
  for (const candidate of list) {
    if (await pingServer(candidate)) {
      apiBase = candidate;
      if (candidate !== stored) toast('Адрес сервера взят из настроек панели теплицы');
      return apiBase;
    }
  }
  const fresh = await published;
  if (fresh && fresh !== (list[0] || '')) {
    if (list.length) toast('Адрес сервера обновлён: туннель перезапускался');
    apiBase = fresh;
    return apiBase;
  }
  apiBase = list[0] || fresh || '';
  return apiBase;
}

function rememberServer(value) {
  const own = storedConnection();
  const panel = panelConnection();
  writeJson(CONN_KEY, {
    apiBase: value,
    apiToken: own.apiToken || panel.apiToken || publishedKey || ''
  });
}

/* --------------------------- вход в аккаунт ----------------------------- */

function loadAuth() {
  const saved = readJson(AUTH_KEY);
  auth = saved && saved.token
    ? { token: saved.token, user: saved.user || null }
    : { token: '', user: null };
  renderUser();
}

function saveAuth() {
  if (auth.token) {
    writeJson(AUTH_KEY, { token: auth.token, user: auth.user });
  } else {
    try {
      localStorage.removeItem(AUTH_KEY);
    } catch (error) {
      /* приватный режим: просто не запомним */
    }
  }
  renderUser();
}

function renderUser() {
  const name = auth.user ? auth.user.username : '';
  $('#user-name').textContent = name || '—';
  show('#user-pill', Boolean(name));
  show('#logout', Boolean(auth.token));
}

function setAuthMode(form) {
  const register = form !== 'login';
  $('#auth-title').textContent = register ? 'Регистрация' : 'Вход в игру';
  $('#auth-submit').textContent = register ? 'Зарегистрироваться' : 'Войти';
  $('#auth-toggle').textContent = register ? 'У меня уже есть аккаунт' : 'Создать аккаунт';
  $('#auth-hint').textContent = register
    ? 'Аккаунт нужен, чтобы прогоны сохранялись за вами. Он же открывает панель теплицы.'
    : 'Войдите тем же логином, что и в панели теплицы.';
  show('#auth-confirm-field', register);
  show('#auth-error', false);
  $('#auth-card').dataset.mode = register ? 'register' : 'login';
}

async function submitAuth() {
  const form = $('#auth-card').dataset.mode === 'login' ? 'login' : 'register';
  const username = ($('#auth-user').value || '').trim();
  const password = $('#auth-pass').value || '';
  const fail = (message) => {
    const box = $('#auth-error');
    box.textContent = message;
    show('#auth-error', true);
  };

  if (!username || !password) return fail('Заполните логин и пароль');
  if (form === 'register' && password !== $('#auth-confirm').value) return fail('Пароли не совпадают');

  const button = $('#auth-submit');
  button.disabled = true;
  try {
    const data = await api('/api/auth/' + form, { method: 'POST', body: { username, password } });
    auth = { token: data.token, user: data.user };
    saveAuth();
    toast(form === 'register' ? 'Аккаунт создан — можно собирать состав'
      : 'С возвращением, ' + (data.user && data.user.username));
    show('#auth-card', false);
    await afterAuth();
  } catch (error) {
    fail(error.status === 429 ? 'Слишком много попыток, подождите минуту'
      : (error.message || 'Не удалось выполнить запрос'));
  } finally {
    button.disabled = false;
  }
}

function signOut() {
  if (auth.token) {
    api('/api/auth/logout', { method: 'POST' }).catch(() => {});
  }
  auth = { token: '', user: null };
  saveAuth();
  run = null;
  journal = [];
  pendingPlayer = '';
  stopPolling();
  hideAll();
  showAuth('register');
}

/* ------------------------------ экраны ---------------------------------- */

function hideAll() {
  ['#lobby', '#draft', '#run'].forEach((selector) => show(selector, false));
}

function showAuth(form) {
  setAuthMode(form);
  show('#auth-card', true);
  hideAll();
  $('#auth-user').focus();
}

async function showLobby() {
  run = null;
  pendingPlayer = '';
  stopPolling();
  hideAll();
  show('#lobby', true);
  if (!catalog.length) await loadCatalog();
  if (!gameKey) return;
  await loadStatus();
  await loadJournal(journalScope);
}

/* ------------------------------ игры ------------------------------------ */

function savedGame() {
  const saved = readJson(GAME_KEY) || {};
  return String(saved.game || '');
}

/* Выбранная игра переживает перезагрузку страницы. */
function rememberGame(key) {
  writeJson(GAME_KEY, { game: key });
}

async function loadCatalog() {
  try {
    const data = await api(DRAFT + '/games');
    catalog = data.games || [];
  } catch (error) {
    catalog = [];
    if (!sessionExpired(error)) toast(failMessage(error), 'err');
    return;
  }
  if (!catalog.length) return;
  const keys = catalog.map((item) => item.key);
  /* Игра задана самой страницей: выбора нет, и запоминать нечего. */
  if (PRESET_GAME) {
    gameKey = PRESET_GAME;
    if (keys.indexOf(gameKey) < 0) {
      toast('Сервер не знает игру «' + gameKey + '»: подписи придут от страницы.', 'err');
    }
    applyGameBlock();
    return;
  }
  const saved = savedGame();
  gameKey = keys.indexOf(saved) >= 0 ? saved
    : (keys.indexOf(DEFAULT_GAME) >= 0 ? DEFAULT_GAME : keys[0]);
  /* Игра такая же, как и в следующий заход: даже если выбор сделан по
     умолчанию, страница откроется на ней же. */
  rememberGame(gameKey);
  applyGameBlock();
}

function applyGameBlock() {
  const found = catalog.filter((item) => item.key === gameKey)[0];
  if (found) game = found;
  renderGameChoices();
  renderGameTexts();
}

/* Смена игры: сервер рассказывает про неё всё сам, поэтому подписи
   интерфейса обновляются вместе с набором и текущим прогоном. */
async function setGame(key) {
  if (!key || key === gameKey) return;
  gameKey = key;
  rememberGame(key);
  applyGameBlock();
  run = null;
  pendingPlayer = '';
  stopPolling();
  hideAll();
  show('#lobby', true);
  await loadStatus();
  await loadJournal('mine');
}

function renderGameChoices() {
  const node = $('#game-choices');
  /* Игра задана самой страницей: переключать нечего — поле выбора убираем. */
  if (PRESET_GAME) {
    node.innerHTML = '';
    show('#game-field', false);
    return;
  }
  show('#game-field', true);
  if (!catalog.length) {
    node.innerHTML = '<span class="muted">Список игр не получен — проверьте адрес сервера.</span>';
    return;
  }
  node.innerHTML = catalog.map((item) => (
    '<button type="button" class="choice' + (item.key === gameKey ? ' on' : '') + '"'
    + ' data-kind="game" data-key="' + escapeHtml(item.key) + '">'
    + '<b>' + escapeHtml(item.title) + '</b>'
    + '<span>' + escapeHtml(item.tagline) + '</span></button>'
  )).join('');
}

/* Подписи берутся из ответа сервера: страница не знает ни одной игры. */
function renderGameTexts() {
  if (!game) return;
  document.title = game.title + ' · драфт-рогалик · Умная AI-Теплица';
  $('#brand-title').textContent = game.title;
  $('#brand-tagline').textContent = game.tagline;
  $('#game-help').innerHTML = (game.help || []).map(
    (text) => '<p class="muted">' + escapeHtml(text) + '</p>'
  ).join('');
  $('#pool-label').textContent = game.pool_label;
  $('#pool-hint-label').textContent = '— ' + game.pool_hint;
  $('#pack-pool-label').textContent = game.match.arena_cap;
  $('#pack-pool-hint').textContent = '— ' + game.pool_item_hint;
  $('#start-run').textContent = game.boot_title;
}

const arenaWord = () => (game && game.match ? game.match.arena : 'площадка');

/* Правило матча словами игры: «Раунды до победы: 13». */
function matchRule() {
  return cap(game.match.score) + ' до победы: ' + game.match.rounds_to_win;
}

function eraLabel(key) {
  const labels = (game && game.era_labels) || {};
  return labels[key] || key || '';
}

function difficultyLabel(key) {
  const found = info ? info.difficulties.filter((item) => item.key === key)[0] : null;
  return found ? found.label : (key || '');
}

function stageLabel(key) {
  const found = info ? info.stages.filter((stage) => stage.key === key)[0] : null;
  return found ? found.title : (key || 'вылет');
}

const championLabel = () => cap(game.tournament) + ' взят';

/* --------------------------- состояние набора --------------------------- */

async function loadStatus() {
  if (!gameKey) return;
  try {
    info = await api(gamePath() + '/status');
  } catch (error) {
    info = null;
    if (!sessionExpired(error)) toast(failMessage(error), 'err');
    return;
  }
  if (info.game) game = info.game;
  renderGameTexts();
  renderChoices();
  renderPool();
}

function renderChoices() {
  renderGameChoices();
  if (!info) return;

  $('#difficulty').innerHTML = info.difficulties.map((item) => (
    '<button type="button" class="choice' + (item.key === pick.difficulty ? ' on' : '') + '"'
    + ' data-kind="difficulty" data-key="' + escapeHtml(item.key) + '">'
    + '<b>' + escapeHtml(item.label) + '</b>'
    + '<span>рероллов: ' + item.rerolls + '</span></button>'
  )).join('');

  const eras = Object.keys(info.eras).filter((key) => info.eras[key]);
  if (eras.length && eras.indexOf(pick.era) < 0) pick.era = eras[0];
  $('#era').innerHTML = eras.map((key) => (
    '<button type="button" class="choice' + (key === pick.era ? ' on' : '') + '"'
    + ' data-kind="era" data-key="' + escapeHtml(key) + '">'
    + '<b>' + escapeHtml(eraLabel(key)) + '</b>'
    + '<span>составов: ' + info.eras[key] + '</span></button>'
  )).join('');

  $('#assign').innerHTML = [
    { key: 'auto', label: 'Автоматически', hint: 'игрок встаёт в лучшую свободную роль' },
    { key: 'manual', label: 'Вручную', hint: 'слот выбираете вы при выборе игрока' }
  ].map((item) => (
    '<button type="button" class="choice' + (item.key === pick.assign ? ' on' : '') + '"'
    + ' data-kind="assign" data-key="' + item.key + '">'
    + '<b>' + item.label + '</b><span>' + item.hint + '</span></button>'
  )).join('');
}

function renderPool() {
  if (!info) return;
  const node = $('#pool-hint');
  const ready = info.ready[pick.era] !== false && info.packs > 0;
  const stages = info.stages.map((stage) => stage.title + ' (Bo' + stage.best_of + ')').join(' → ');
  node.textContent = 'Составов в базе: ' + info.packs + '. Стадии прогона: ' + stages + '.';
  $('#start').disabled = !ready;
  $('#lobby-badge').textContent = ready ? ('составов: ' + info.packs) : 'составов нет';
  if (!ready) {
    node.textContent += ' Составов не хватает: владелец сайта наполняет базу этой игры.';
  }
}

/* ------------------------------- журнал --------------------------------- */

async function loadJournal(scope) {
  if (!gameKey) return;
  journalScope = scope === 'all' ? 'all' : 'mine';
  const query = journalScope === 'all' ? '?limit=20&scope=all' : '?limit=20';
  try {
    const data = await api(gamePath() + '/matches' + query);
    journal = data.matches || [];
  } catch (error) {
    journal = [];
    if (!sessionExpired(error)) toast(failMessage(error), 'err');
  }
  renderJournal();
}

function renderJournal() {
  const node = $('#journal');
  $('#journal-badge').textContent = journal.length ? ('прогонов: ' + journal.length) : 'пока пусто';
  /* Журнал всех прогонов открыт только администратору: у обычного 403. */
  const admin = Boolean(auth.user && auth.user.role === 'admin');
  show('#journal-scope', admin);
  if (admin) {
    $('#journal-scope').textContent = journalScope === 'all' ? 'Только мои' : 'Все прогоны';
  }
  if (!journal.length) {
    node.innerHTML = '<p class="muted">Здесь появятся законченные прогоны: состав,'
      + ' сложность и результат.</p>';
    return;
  }
  node.innerHTML = journal.map((item) => (
    '<div class="row-item"><div class="head">'
    + '<span class="title">#' + item.id + ' · ' + escapeHtml(item.squad || '—') + '</span>'
    + '<span class="' + (item.champion ? 'win' : 'loss') + '">'
    + (item.champion ? escapeHtml(championLabel()) : escapeHtml(stageLabel(item.stage)))
    + ' (' + item.wins + ':' + item.losses + ')</span></div>'
    + '<span class="sub">' + escapeHtml(difficultyLabel(item.difficulty)) + ' · '
    + escapeHtml(eraLabel(item.era)) + ' · сила состава ' + num(item.rating) + '</span>'
    + (item.score ? '<span class="sub">' + escapeHtml(item.score) + '</span>' : '')
    + (journalScope === 'all'
      ? '<span class="sub">игрок: ' + escapeHtml(item.username || '—') + '</span>' : '')
    + '</div>'
  )).join('');
}

/* -------------------------------- драфт --------------------------------- */

async function startRun() {
  await act('POST', '/runs',
    { difficulty: pick.difficulty, era: pick.era, assign: pick.assign },
    'Прогон начался: соберите состав');
}

function renderDraft() {
  const packing = run.pack;
  $('#draft-badge').textContent = run.ready ? 'состав собран' : 'драфт';
  $('#rerolls').textContent = run.rerolls;
  $('#reroll').disabled = run.rerolls <= 0;
  $('#start-run').disabled = !run.ready;
  renderAssignChoices();

  const fit = run.rating.fit;
  $('#rating').innerHTML = [
    { label: 'Игроки', value: num(run.rating.base) },
    { label: 'Роли', value: (fit >= 0 ? '+' : '') + num(fit) },
    { label: 'Сыгранность', value: '+' + num(run.rating.chemistry) },
    { label: 'Усиления', value: '+' + num(run.rating.boosts) },
    { label: 'Сила состава', value: num(run.rating.total), total: true }
  ].map((cell) => (
    '<div class="cell' + (cell.total ? ' total' : '') + '"><span>' + cell.label
    + '</span><b>' + cell.value + '</b></div>'
  )).join('');

  /* Слотов ровно столько, сколько ролей у игры: в RL это три, не пять. */
  $('#squad').innerHTML = run.roles.map((role) => {
    const player = run.squad[role.key];
    if (!player) {
      return '<div class="slot"><span class="role">' + escapeHtml(role.label)
        + '</span><span class="who muted">пусто</span></div>';
    }
    const fitClass = player.fit > 0 ? 'good' : (player.fit < 0 ? 'bad' : '');
    const fitText = player.fit > 0 ? 'своя роль'
      : (player.fit < 0 ? 'не его роль' : 'родственная роль');
    return '<div class="slot filled"><span class="role">'
      + escapeHtml(player.slot_label || role.label) + '</span>'
      + '<span class="who">' + escapeHtml(player.name) + '</span>'
      + '<span class="where">' + num(player.ovr) + ' · ' + escapeHtml(player.role_label) + '</span>'
      + '<span class="fit ' + fitClass + '">' + fitText + '</span></div>';
  }).join('');

  $('#pool-label').textContent = game.pool_label + ': ' + run.pool.length
    + ' из ' + run.pool_limit;
  $('#map-pool').innerHTML = run.pool.length
    ? run.pool.map((name) => '<span class="map-chip mine">' + escapeHtml(name) + '</span>').join('')
    : '<span class="muted">Пока пусто: ' + escapeHtml(game.pool_item_hint) + '.</span>';

  $('#pack-team').textContent = packing.team;
  $('#pack-meta').textContent = [packing.event, packing.year, packing.place,
    packing.region, eraLabel(packing.era)].filter(Boolean).join(' · ');

  $('#pack-maps').innerHTML = packing.maps.map((name) => {
    const mine = run.pool.indexOf(name) >= 0;
    const full = run.pool.length >= run.pool_limit;
    return '<button type="button" class="map-chip' + (mine ? ' mine' : '') + '"'
      + ' data-map="' + escapeHtml(name) + '" title="' + escapeHtml(game.pool_label) + '"'
      + (mine || full ? ' disabled' : '') + '>'
      + escapeHtml(name) + (mine ? ' ✓' : '') + '</button>';
  }).join('');

  const taken = Object.keys(run.squad).map((slot) => run.squad[slot])
    .filter(Boolean).map((player) => player.name.toLowerCase());
  $('#pack-players').innerHTML = packing.players.map((player) => {
    const isTaken = taken.indexOf(player.name.toLowerCase()) >= 0;
    return '<div class="player-row' + (isTaken ? ' taken' : '') + '">'
      + '<span class="role-tag">' + escapeHtml(player.role_label) + '</span>'
      + '<span class="who">' + escapeHtml(player.name) + '</span>'
      + '<span class="stats">AIM ' + num(player.aim) + ' · CLUTCH ' + num(player.clutch)
      + ' · IMP ' + num(player.impact) + '</span>'
      + '<span class="row" style="gap:10px;justify-content:flex-end;">'
      + '<span class="ovr">' + num(player.ovr) + '</span>'
      + '<button type="button" class="btn btn-sm ' + (isTaken ? 'btn-ghost' : 'btn-primary')
      + '" data-player="' + escapeHtml(player.name) + '"' + (isTaken ? ' disabled' : '') + '>'
      + (isTaken ? 'в составе' : 'Взять') + '</button></span></div>';
  }).join('');

  renderRoleChooser();
  renderFeed($('#draft-feed'), run.log.slice(-6));
  $('#draft-hint').textContent = run.ready
    ? 'Состав собран: нажмите «' + game.boot_title + '» — впереди '
      + info.stages.map((stage) => stage.title).join(', ') + '.'
    : 'Нужны все роли: слотов ' + run.roles.length + '. За свою роль игрок получает'
      + ' надбавку, за чужую — штраф; игроки из одного состава дают сыгранность.'
      + ' Своя ' + arenaWord() + ' в пуле даёт надбавку.';
}

function renderAssignChoices() {
  $('#run-assign').innerHTML = [
    { key: 'auto', label: 'Автоматически', hint: 'игрок встаёт в лучшую свободную роль' },
    { key: 'manual', label: 'Вручную', hint: 'слот выбираете вы при выборе игрока' }
  ].map((item) => (
    '<button type="button" class="choice' + (item.key === run.assign ? ' on' : '') + '"'
    + ' data-assign="' + item.key + '"><b>' + item.label + '</b>'
    + '<span>' + item.hint + '</span></button>'
  )).join('');
}

function renderRoleChooser() {
  const node = $('#role-chooser');
  if (!pendingPlayer) {
    show('#role-chooser', false);
    node.innerHTML = '';
    return;
  }
  const free = run.roles.filter((role) => !run.squad[role.key]);
  show('#role-chooser', true);
  node.innerHTML = '<span class="muted">Куда поставить ' + escapeHtml(pendingPlayer) + '?</span>'
    + free.map((role) => '<button type="button" class="btn btn-sm btn-ghost" data-slot="'
      + escapeHtml(role.key) + '">' + escapeHtml(role.label) + '</button>').join('')
    + '<button type="button" class="btn btn-sm btn-ghost" data-slot="cancel">Отмена</button>';
}

async function takePlayer(player) {
  if (run.assign === 'manual' && !pendingPlayer) {
    pendingPlayer = player;
    renderRoleChooser();
    return;
  }
  pendingPlayer = '';
  await act('POST', '/runs/' + run.id + '/take', { player }, 'Игрок в составе');
}

async function takeMap(name) {
  await act('POST', '/runs/' + run.id + '/map', { map: name }, 'Площадка в своём пуле');
}

/* -------------------------------- прогон -------------------------------- */

function renderRun() {
  const stage = run.stage;
  $('#stage-title').textContent = stage.title + ' · ' + (stage.index + 1) + ' из ' + stage.total;
  $('#run-badge').textContent = 'Bo' + stage.best_of + ' · ' + run.difficulty_label;
  $('#run-rating').innerHTML = 'Сила состава: <b>' + num(run.rating.total) + '</b>'
    + ' · ' + escapeHtml(game.pool_label) + ': <b>' + run.pool.length + '</b>'
    + ' · ' + escapeHtml(matchRule())
    + ' · усилений: <b>' + run.boosts.length + '</b>'
    + ' · рероллов: <b>' + run.rerolls + '</b>';

  $('#run-squad').innerHTML = run.roles.map((role) => {
    const player = run.squad[role.key];
    if (!player) return '';
    return '<div class="slot filled"><span class="role">'
      + escapeHtml(player.slot_label || role.label) + '</span>'
      + '<span class="who">' + escapeHtml(player.name) + '</span>'
      + '<span class="where">' + num(player.ovr) + ' · ' + escapeHtml(player.role_label)
      + '</span></div>';
  }).join('');

  const finished = run.status === 'dead' || run.status === 'champion';
  const wins = run.history.filter((item) => item.won).length;
  $('#play-stage').disabled = finished || !run.ready || run.reward.length > 0;
  $('#play-stage').textContent = run.history.length
    ? 'Играть следующую стадию' : 'Играть стадию';
  $('#run-hint').textContent = finished ? 'Прогон закончен.'
    : (run.reward.length ? 'Сначала выберите усиление.'
      : 'Своя ' + arenaWord() + ' в пуле даёт надбавку. ' + matchRule() + '.');

  show('#reward-card', run.reward.length > 0);
  $('#reward').innerHTML = run.reward.map((boost, index) => (
    '<div class="boost"><b>' + escapeHtml(boost.title) + '</b>'
    + '<button type="button" class="btn btn-sm btn-primary" data-boost="' + index
    + '">Взять</button></div>'
  )).join('');

  $('#matches-badge').textContent = run.history.length
    ? (wins + ' побед') : 'матчей пока нет';
  renderMatches();

  show('#finish-card', finished);
  if (finished) {
    const champion = run.status === 'champion';
    $('#finish-title').textContent = champion ? championLabel() + '!' : 'Прогон закончен';
    $('#finish-badge').textContent = champion ? 'идеальный прогон' : 'вылет';
    $('#finish-text').textContent = (champion
      ? 'Состав прошёл все стадии без поражений. '
      : 'Поражение завершает прогон — так устроен рогалик. ')
      + 'Итог: ' + wins + ' побед, ' + (run.history.length - wins) + ' поражений.'
      + ' Сила состава: ' + num(run.rating.total) + '.';
  }
}

function renderMatches() {
  const node = $('#matches');
  if (!run.history.length) {
    node.innerHTML = '<p class="muted">Матчи появятся здесь: соперник, счёт и '
      + escapeHtml(game.match.score) + '.</p>';
    return;
  }
  node.innerHTML = run.history.map((match) => (
    '<div class="match"><div class="head">'
    + '<span class="stage">' + escapeHtml(match.stage_title) + ' · Bo' + match.best_of
    + ' · против ' + escapeHtml(match.opponent.team) + ' ('
    + escapeHtml(match.opponent.event) + ')</span>'
    + '<span class="score ' + (match.won ? 'win' : 'lose') + '">'
    + escapeHtml(match.score) + '</span></div>'
    + '<div class="maps-line">' + (match.log || []).map((row) => (
      '<div><span class="' + (row.ours_map ? 'mine' : '') + '">' + escapeHtml(row.map)
      + (row.ours_map ? ' (' + arenaWord() + ' из пула)' : '') + '</span>'
      + '<span>' + row.ours + ':' + row.theirs
      + (row.overtime ? ' <span class="ot">ОТ</span>' : '') + '</span></div>'
    )).join('') + '</div></div>'
  )).join('');
}

function renderFeed(node, entries) {
  if (!entries || !entries.length) {
    node.innerHTML = '<p class="muted">Здесь видно, что происходит в прогоне.</p>';
    return;
  }
  node.innerHTML = entries.map((entry) => (
    '<div class="match"><div class="head"><span class="stage">' + escapeHtml(entry.text)
    + '</span></div></div>'
  )).join('');
}

/* ------------------------------- действия -------------------------------- */

async function act(method, path, body, message) {
  if (busy) return;
  busy = true;
  try {
    const data = await api(gamePath() + path, { method, body });
    applyRun(data.state);
    if (message) toast(message);
  } catch (error) {
    if (!sessionExpired(error)) toast(failMessage(error), 'err');
  } finally {
    busy = false;
  }
}

function applyRun(state, silent) {
  if (!state) return;
  if (silent && run && run.id === state.id && JSON.stringify(state) === JSON.stringify(run)) return;
  run = state;
  hideAll();
  if (state.status === 'draft' || state.status === 'ready') {
    show('#draft', true);
    renderDraft();
  } else {
    show('#run', true);
    renderRun();
  }
  syncPoller();
}

/* Пока прогон не закончен, страница сама подтягивает его состояние. */
function syncPoller() {
  const active = Boolean(run) && run.status !== 'dead' && run.status !== 'champion';
  if (active && !poller) poller = window.setInterval(pollRun, POLL_MS);
  if (!active) stopPolling();
}

function stopPolling() {
  if (poller) {
    window.clearInterval(poller);
    poller = 0;
  }
}

async function pollRun() {
  if (!run || !run.id || busy || pendingPlayer || document.hidden) return;
  const id = run.id;
  try {
    const data = await api(gamePath() + '/runs/' + id);
    if (!run || run.id !== id) return;
    applyRun(data.state, true);
  } catch (error) {
    /* Опрос не должен мешать игре: 401 разбираем, остальное ждём молча. */
    sessionExpired(error);
  }
}

/* ------------------------------ соединение ------------------------------- */

let connSeq = 0;

async function checkConnection() {
  const seq = ++connSeq;
  const apply = (kind, text) => {
    if (seq === connSeq) setConnection(kind, text);
  };
  const served = ['http:', 'https:'].indexOf(location.protocol) >= 0;
  if (!root() && !served) {
    apply('err', 'адрес не задан');
    return false;
  }
  try {
    await api('/api/health');
    apply('online', 'на связи');
    return true;
  } catch (error) {
    if (error.status === 401) {
      // Сервер жив, просто закрыт общим ключом — игре это не мешает.
      apply('online', 'на связи');
      return true;
    }
    apply('err', root() ? 'сервер не отвечает' : 'API на этом домене нет');
    return false;
  }
}

async function afterAuth() {
  const ok = await checkConnection();
  if (!ok) {
    $('#srv-input').value = root();
    show('#server-card', true);
    return;
  }
  show('#server-card', false);
  await showLobby();
}

async function boot() {
  applyTheme(readJson(THEME_KEY) || readJson(PANEL_STATE_KEY) || {});
  loadAuth();
  /* Адрес берём из ссылки, своих сохранённых настроек или панели теплицы
     и сразу проверяем, что он живой — вводить вручную не нужно. */
  await resolveApiBase();
  $('#srv-input').value = root();
  await loadCatalog();

  $('#auth-submit').addEventListener('click', submitAuth);
  $('#auth-toggle').addEventListener('click', () => {
    setAuthMode($('#auth-card').dataset.mode === 'login' ? 'register' : 'login');
  });
  $('#auth-card').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      submitAuth();
    }
  });
  $('#logout').addEventListener('click', signOut);
  $('#toggle-theme').addEventListener('click', toggleTheme);
  $('#srv-save').addEventListener('click', async () => {
    apiBase = ($('#srv-input').value || '').trim().replace(/\/+$/, '');
    rememberServer(apiBase);
    await afterAuth();
  });

  $('#lobby').addEventListener('click', (event) => {
    const choice = event.target.closest('.choice');
    if (choice) {
      if (choice.dataset.kind === 'game') return void setGame(choice.dataset.key);
      pick[choice.dataset.kind] = choice.dataset.key;
      renderChoices();
      renderPool();
      return;
    }
    if (event.target.closest('#start')) return void startRun();
    if (event.target.closest('#journal-scope')) {
      return void loadJournal(journalScope === 'all' ? 'mine' : 'all');
    }
  });

  $('#draft').addEventListener('click', (event) => {
    const player = event.target.closest('[data-player]');
    if (player) return void takePlayer(player.dataset.player);
    const map = event.target.closest('[data-map]');
    if (map) return void takeMap(map.dataset.map);
    const assign = event.target.closest('[data-assign]');
    if (assign) {
      return void act('POST', '/runs/' + run.id + '/assign',
        { mode: assign.dataset.assign }, 'Способ расстановки изменён');
    }
    const slot = event.target.closest('[data-slot]');
    if (slot) {
      if (slot.dataset.slot === 'cancel') {
        pendingPlayer = '';
        return void renderRoleChooser();
      }
      const name = pendingPlayer;
      pendingPlayer = '';
      return void act('POST', '/runs/' + run.id + '/take',
        { player: name, role: slot.dataset.slot }, 'Игрок в составе');
    }
    if (event.target.closest('#auto-assign')) {
      return void act('POST', '/runs/' + run.id + '/auto', null, 'Роли расставлены');
    }
    if (event.target.closest('#skip-pack')) {
      return void act('POST', '/runs/' + run.id + '/pack', null, 'Предложен другой состав');
    }
    if (event.target.closest('#reroll')) {
      return void act('POST', '/runs/' + run.id + '/reroll', null, 'Реролл потрачен');
    }
    if (event.target.closest('#start-run')) {
      return void act('POST', '/runs/' + run.id + '/play', null, 'Турнир начался');
    }
    if (event.target.closest('#to-lobby-draft')) {
      return void showLobby();
    }
  });

  $('#run').addEventListener('click', (event) => {
    if (event.target.closest('#play-stage')) {
      return void act('POST', '/runs/' + run.id + '/play', null, '');
    }
    const boost = event.target.closest('[data-boost]');
    if (boost) {
      return void act('POST', '/runs/' + run.id + '/boost',
        { index: Number(boost.dataset.boost) }, 'Усиление взято');
    }
    if (event.target.closest('#again') || event.target.closest('#to-lobby')) {
      return void showLobby();
    }
  });

  if (auth.token) {
    try {
      const data = await api('/api/auth/me');
      auth.user = data.user || auth.user;
      saveAuth();
      await afterAuth();
    } catch (error) {
      if (error.status === 401) {
        auth = { token: '', user: null };
        saveAuth();
        showAuth('login');
      } else {
        showAuth('login');
        show('#server-card', true);
      }
    }
    return;
  }

  if (!(await checkConnection())) {
    $('#srv-input').value = root();
    show('#server-card', true);
  }
  showAuth('register');
}

/* -------------------------------- тема ---------------------------------- */

function applyTheme(saved) {
  document.documentElement.dataset.theme = saved && saved.theme === 'dark' ? 'dark' : 'light';
}

function toggleTheme() {
  const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = next;
  writeJson(THEME_KEY, { theme: next });
}

document.addEventListener('DOMContentLoaded', () => {
  boot().catch((error) => toast('Не удалось запустить игру: ' + error.message, 'err'));
});
