/* ==========================================================================
   Умная AI-Теплица — фронтенд панели управления
   Чистый JS без сборщиков: работает и по file://, и через Live Server.
   Если бэкенд доступен (GET /api/state) — берём данные оттуда,
   иначе панель работает в демонстрационном режиме.
   ========================================================================== */
'use strict';

const STORAGE_KEY = 'greenhouse.state.v1';
const TICK_MS = 2000;
const MAX_POINTS = 60;

const MODE_NAMES = { auto: 'Авто', eco: 'Эко', boost: 'Интенсив', manual: 'Ручной' };

const DEVICE_LABELS = {
  watering: { on: 'насос работает', off: 'выключен' },
  ventilation: { on: 'проветривание идёт', off: 'закрыто' },
  lighting: { on: 'фитолампы включены', off: 'выключены' }
};

const ZONE_COUNT = 12;

const DEFAULTS = {
  view: 'dashboard',
  theme: 'light',
  mode: 'auto',
  target: 55,
  tank: 78,
  windowOpen: 0,
  photoperiod: 14,
  wateringDuration: 10,
  ventilationDuration: 30,
  apiBase: '',
  sensors: { temperature: 24.6, moisture: 48, light: 12400 },
  thresholds: { moisture: 35, temperature: 30, light: 8000 },
  auto: { watering: true, ventilation: true, lighting: false },
  devices: {
    watering: { on: false },
    ventilation: { on: false },
    lighting: { on: false }
  },
  zones: [],          // 12 участков теплицы: данные с сервера или демо-симуляция
  selectedZone: 1,
  history: { temperature: [], moisture: [], light: [], tank: [] },
  logs: [],
  logFilter: 'all',
  online: false,
  source: 'simulator'
};

let deferredPrompt = null; // событие установки PWA (не сериализуется в localStorage)

/* ------------------------------- утилиты ---------------------------------- */

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const clone = (value) => JSON.parse(JSON.stringify(value));

function getPath(object, path) {
  return path.split('.').reduce((acc, key) => (acc == null ? acc : acc[key]), object);
}

function setPath(object, path, value) {
  const keys = path.split('.');
  const last = keys.pop();
  const target = keys.reduce((acc, key) => {
    if (typeof acc[key] !== 'object' || acc[key] === null) acc[key] = {};
    return acc[key];
  }, object);
  target[last] = value;
}

function mergeDefaults(target, source) {
  for (const [key, value] of Object.entries(source)) {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      target[key] = mergeDefaults(typeof target[key] === 'object' && target[key] !== null ? target[key] : {}, value);
    } else if (target[key] === undefined) {
      target[key] = value;
    }
  }
  return target;
}

const FORMATTERS = {
  fixed0: (v) => Number(v).toFixed(0),
  fixed1: (v) => Number(v).toFixed(1),
  int: (v) => Math.round(Number(v)).toLocaleString('ru-RU'),
  default: (v) => String(v)
};

const timeLabel = (iso) =>
  new Date(iso).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
const round1 = (value) => Math.round(value * 10) / 10;

/* -------------------------------- состояние ------------------------------- */

let state = loadState();
let pulseTimers = {};

function loadState() {
  const base = clone(DEFAULTS);
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) mergeDefaults(base, JSON.parse(raw));
  } catch (error) {
    console.warn('Не удалось прочитать сохранённое состояние:', error);
  }
  return base;
}

function saveState() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (error) {
    console.warn('Не удалось сохранить состояние:', error);
  }
}

/* --------------------------------- журнал --------------------------------- */

function addLog(message, level = 'info') {
  state.logs.unshift({ t: new Date().toISOString(), level, msg: message });
  state.logs = state.logs.slice(0, 200);
}

/* ---------------------------- 12 участков теплицы -------------------------- */

const ZONE_STATUS_LABELS = {
  ok: 'норма',
  dry: 'сухо',
  hot: 'перегрев',
  dark: 'мало света'
};

const ZONE_STATUS_ICONS = { ok: '✅', dry: '💧', hot: '🌡️', dark: '🌑' };

function emptyZoneDevices() {
  return {
    watering: { on: false, remaining: 0 },
    ventilation: { on: false, remaining: 0 },
    lighting: { on: false, remaining: 0 }
  };
}

function makeZone(id) {
  const offset = (id - 6.5) / 6.5; // градиент микроклимата от окна к центру
  return {
    id,
    name: `Участок ${id}`,
    sensors: {
      temperature: round1(24 + offset * 1.2),
      moisture: round1(52 - offset * 6),
      light: Math.round(12000 + offset * 2500)
    },
    devices: emptyZoneDevices(),
    target: state?.target ?? 55,
    status: 'ok'
  };
}

function seedZones() {
  state.zones = Array.from({ length: ZONE_COUNT }, (_, index) => makeZone(index + 1));
}

function zoneById(id) {
  return state.zones.find((zone) => zone.id === Number(id));
}

function zoneStatus(sensors) {
  if (sensors.moisture != null && sensors.moisture < state.thresholds.moisture) return 'dry';
  if (sensors.temperature != null && sensors.temperature > state.thresholds.temperature) return 'hot';
  if (sensors.light != null && sensors.light < state.thresholds.light) return 'dark';
  return 'ok';
}

function setZoneDevice(zoneId, device, isOn, seconds) {
  const zone = zoneById(zoneId);
  if (!zone) return;
  const target = zone.devices[device];
  if (!target) return;
  target.on = Boolean(isOn);
  target.remaining = isOn && seconds ? Number(seconds) : 0;

  // команда на сервер (если панель не в автономном режиме)
  if (state.online) {
    postJSON('/api/devices', { zone_id: zone.id, device, on: Boolean(isOn), seconds: seconds || null });
  }

  const name = zone.name;
  const label = deviceName(device);
  if (isOn) addLog(`${name}: ${label} запущен${seconds ? ` на ${seconds} с` : ''}`);
  else addLog(`${name}: ${label} остановлен`);
  saveState();
  render();
}

function setAllZonesDevice(device, isOn, seconds) {
  (state.zones.length ? state.zones : []).forEach((zone) => {
    zone.devices[device].on = Boolean(isOn);
    zone.devices[device].remaining = isOn && seconds ? Number(seconds) : 0;
  });
  setPath(state, `devices.${device}.on`, Boolean(isOn));
  if (state.online) postJSON('/api/devices', { zone_id: 0, device, on: Boolean(isOn), seconds: seconds || null });
  addLog(`${deviceName(device)}: ${isOn ? 'включено на всех участках' : 'выключено на всех участках'}`);
  saveState();
  render();
}

async function postJSON(path, payload) {
  const base = (state.apiBase || '').replace(/\/$/, '');
  try {
    await fetch(`${base}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return true;
  } catch (error) {
    console.warn('Не удалось отправить команду:', error);
    return false;
  }
}

function renderZones() {
  const grid = $('#zone-grid');
  if (!grid) return;
  if (!state.zones.length) seedZones();

  const selected = Number(state.selectedZone) || 1;

  grid.innerHTML = state.zones.map((zone) => {
    const s = zone.sensors;
    const dev = zone.devices;
    const status = zone.status || 'ok';
    const active = zone.id === selected ? ' selected' : '';
    const moisture = s.moisture ?? 0;
    return `
      <article class="zone-card${active}" data-zone="${zone.id}">
        <header class="zone-head">
          <button class="zone-title" type="button" data-action="select-zone" data-zone="${zone.id}">
            <b>${zone.name}</b>
          </button>
          <span class="zone-status ${status}" title="${ZONE_STATUS_LABELS[status]}">
            ${ZONE_STATUS_ICONS[status]} ${ZONE_STATUS_LABELS[status]}
          </span>
        </header>
        <div class="zone-metrics">
          <span title="Влажность почвы">💧 <b>${FORMATTERS.fixed0(moisture)}</b>%</span>
          <span title="Температура">🌡️ <b>${s.temperature != null ? FORMATTERS.fixed1(s.temperature) : '—'}</b>°C</span>
          <span title="Освещённость">☀️ <b>${s.light != null ? FORMATTERS.int(s.light) : '—'}</b> лк</span>
        </div>
        <div class="zone-bar" title="Влажность ${FORMATTERS.fixed0(moisture)}%">
          <span style="width:${clamp(moisture, 0, 100)}%"></span>
        </div>
        <div class="zone-actions">
          <button class="btn btn-sm ${dev.watering.on ? 'btn-primary' : 'btn-ghost'}"
                  type="button" data-action="zone-device" data-zone="${zone.id}" data-device="watering">
            ${dev.watering.on ? `💦 ${dev.watering.remaining ? Math.ceil(dev.watering.remaining) + ' с' : 'идёт'}` : '💦 Полить'}
          </button>
          <button class="btn btn-sm ${dev.ventilation.on ? 'btn-primary' : 'btn-ghost'}"
                  type="button" data-action="zone-device" data-zone="${zone.id}" data-device="ventilation">
            ${dev.ventilation.on ? '🌬️ идёт' : '🌬️ Продуть'}
          </button>
          <button class="switch switch-sm${dev.lighting.on ? ' on' : ''}" type="button" role="switch"
                  aria-checked="${dev.lighting.on}" data-action="zone-device" data-zone="${zone.id}"
                  data-device="lighting" aria-label="Досветка ${zone.name}"></button>
        </div>
      </article>`;
  }).join('');

  // сводка по участкам
  const ok = state.zones.filter((zone) => zone.status === 'ok').length;
  const dry = state.zones.filter((zone) => zone.status === 'dry').length;
  const hot = state.zones.filter((zone) => zone.status === 'hot').length;
  const watering = state.zones.filter((zone) => zone.devices.watering.on).length;

  const setText = (selector, value) => { const node = $(selector); if (node) node.textContent = value; };
  setText('#zones-ok', `${ok} из ${state.zones.length}`);
  setText('#zones-dry', dry);
  setText('#zones-hot', hot);
  setText('#zones-watering', watering);

  const sourceLabel = state.online
    ? (state.source === 'arduino' ? 'Arduino' : 'сервер · эмулятор')
    : 'автономный режим';
  setText('#zones-source', sourceLabel);
  setText('#zones-source-2', sourceLabel);

  if (state.zones.length === ZONE_COUNT) {
    const moistures = state.zones.map((zone) => zone.sensors.moisture ?? 0);
    drawChart($('#chart-zones'), moistures, { min: 0, max: 100, target: state.target, color: cssVar('--water') || '#3a9bd9' });
  }
}

/* ---------------------------------- роутер -------------------------------- */

function switchView(name, updateHash = true) {
  if (!$(`.view[data-view="${name}"]`)) name = 'dashboard';
  state.view = name;

  $$('.view').forEach((section) => {
    section.hidden = section.dataset.view !== name;
  });
  $$('.tab').forEach((tab) => {
    tab.classList.toggle('active', tab.dataset.view === name);
  });

  if (updateHash && location.hash.slice(1) !== name) {
    try {
      history.replaceState(null, '', `#${name}`);
    } catch (error) {
      location.hash = name; // запасной вариант для открытия файла напрямую
    }
  }
  saveState();
  render();
}

function initRouter() {
  const initial = location.hash.slice(1) || state.view || 'dashboard';
  switchView(initial, false);

  window.addEventListener('hashchange', () => switchView(location.hash.slice(1) || 'dashboard', false));
  $('#tabs').addEventListener('click', (event) => {
    const tab = event.target.closest('.tab');
    if (tab) switchView(tab.dataset.view);
  });
}

/* --------------------------------- отрисовка ------------------------------ */

function bindValues() {
  const dew = round1(state.sensors.temperature - (100 - state.sensors.moisture) / 5);
  setPath(state, 'dewPoint', dew);

  $$('[data-bind]').forEach((node) => {
    const value = getPath(state, node.dataset.bind);
    if (value === undefined || value === null) return;
    const format = FORMATTERS[node.dataset.format] || FORMATTERS.default;
    node.textContent = format(value);
  });
}

function bindInputs() {
  $$('[data-model]').forEach((input) => {
    const value = getPath(state, input.dataset.model);
    if (input.type === 'checkbox') input.checked = Boolean(value);
    else if (document.activeElement !== input) input.value = value ?? '';
  });
}

function renderSwitches() {
  $$('.switch[data-device]').forEach((button) => {
    const device = button.dataset.device;
    const isOn = Boolean(getPath(state, `devices.${device}.on`));
    button.classList.toggle('on', isOn);
    button.setAttribute('aria-checked', String(isOn));
    const row = button.closest('.device');
    if (row) row.classList.toggle('on', isOn);
  });

  $$('[data-device-status]').forEach((node) => {
    const device = node.dataset.deviceStatus;
    const isOn = Boolean(getPath(state, `devices.${device}.on`));
    node.textContent = DEVICE_LABELS[device][isOn ? 'on' : 'off'];
  });
}

function renderGauge() {
  const gauge = $('#gauge-moisture');
  if (!gauge) return;

  const perimeter = 2 * Math.PI * 52;
  const value = clamp(state.sensors.moisture, 0, 100);
  gauge.style.strokeDashoffset = String(perimeter * (1 - value / 100));

  const verdict = $('#moisture-verdict');
  if (verdict) {
    if (value < state.thresholds.moisture) verdict.textContent = 'сухо — нужен полив';
    else if (value > state.target + 15) verdict.textContent = 'переувлажнение';
    else verdict.textContent = 'норма';
  }
}

function renderExtras() {
  const tankBar = $('#tank-bar');
  if (tankBar) tankBar.style.width = `${clamp(state.tank, 0, 100)}%`;

  const modeBadge = $('#mode-badge');
  if (modeBadge) modeBadge.textContent = `Режим: ${MODE_NAMES[state.mode]}`;

  const lightVerdict = $('#light-verdict');
  if (lightVerdict) {
    const lux = state.sensors.light;
    lightVerdict.textContent =
      lux < 3000 ? 'слишком темно, нужна досветка'
        : lux < 15000 ? 'рассеянный свет, оптимально для рассады'
          : 'яркий свет, отличные условия';
  }

  const ventVerdict = $('#vent-verdict');
  if (ventVerdict) {
    const hot = state.sensors.temperature > state.thresholds.temperature;
    const humid = state.sensors.light < state.thresholds.light;
    ventVerdict.textContent = hot
      ? 'Температура выше комфортной — рекомендуется проветривание.'
      : humid ? 'Температура в норме, проветривание не требуется.'
        : 'Микроклимат стабилен, вмешательство не нужно.';
  }

  $$('.mode').forEach((button) => {
    button.classList.toggle('active', button.dataset.mode === state.mode);
  });
}

function renderLogs() {
  const render = (list, node, limit) => {
    if (!node) return;
    const items = limit ? list.slice(0, limit) : list;
    if (!items.length) {
      node.innerHTML = '<li class="empty">Пока нет событий</li>';
      return;
    }
    node.innerHTML = items
      .map((entry) => `
        <li class="log-item ${entry.level === 'info' ? '' : entry.level}">
          <span class="log-time">${timeLabel(entry.t)}</span>
          <span class="log-msg">${escapeHtml(entry.msg)}</span>
        </li>`)
      .join('');
  };

  const filtered = state.logs.filter((entry) =>
    state.logFilter === 'all' ? true : entry.level === state.logFilter);

  render(filtered, $('#log-preview'), 5);
  render(filtered, $('#log-full'));
  render(state.logs.filter((entry) => /полив|бак|насос/i.test(entry.msg)), $('#log-watering'), 8);
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

/* ---------------------------------- графики ------------------------------- */

function drawChart(canvas, values, options = {}) {
  if (!canvas || canvas.offsetParent === null) return;

  // Размер берём из CSS-рамки: если задавать canvas.height из его же clientHeight,
  // элемент будет «расти» при каждом перерисовывании (размер в атрибуте влияет на layout).
  const box = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const width = Math.round(box.width);
  const height = Math.round(box.height);
  if (width < 2 || height < 2) return;

  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);

  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);

  const pad = { top: 12, right: 10, bottom: 16, left: 10 };
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const min = options.min ?? 0;
  const max = options.max ?? 100;

  const pointX = (index) => pad.left + (values.length < 2 ? innerW / 2 : (innerW * index) / (values.length - 1));
  const pointY = (value) => pad.top + innerH - ((clamp(value, min, max) - min) / (max - min)) * innerH;

  // сетка
  ctx.strokeStyle = cssVar('--grid') || 'rgba(0,0,0,.1)';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 3; i += 1) {
    const y = pad.top + (innerH * i) / 3;
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(width - pad.right, y);
    ctx.stroke();
  }

  if (values.length < 2) return;

  const color = options.color || cssVar('--accent') || '#4f9a48';

  // заливка под линией
  const gradient = ctx.createLinearGradient(0, pad.top, 0, pad.top + innerH);
  gradient.addColorStop(0, hexToRgba(color, 0.35));
  gradient.addColorStop(1, hexToRgba(color, 0.02));

  ctx.beginPath();
  values.forEach((value, index) => {
    const x = pointX(index);
    const y = pointY(value);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.lineTo(pointX(values.length - 1), pad.top + innerH);
  ctx.lineTo(pointX(0), pad.top + innerH);
  ctx.closePath();
  ctx.fillStyle = gradient;
  ctx.fill();

  // линия
  ctx.beginPath();
  values.forEach((value, index) => {
    const x = pointX(index);
    const y = pointY(value);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = color;
  ctx.lineWidth = 2.5;
  ctx.lineJoin = 'round';
  ctx.stroke();

  // целевое значение
  if (options.target !== undefined) {
    const y = pointY(options.target);
    ctx.save();
    ctx.setLineDash([6, 6]);
    ctx.strokeStyle = cssVar('--text-dim') || '#5d6b57';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(width - pad.right, y);
    ctx.stroke();
    ctx.restore();
  }

  // последняя точка
  const lastX = pointX(values.length - 1);
  const lastY = pointY(values[values.length - 1]);
  ctx.beginPath();
  ctx.arc(lastX, lastY, 4.5, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();
  ctx.strokeStyle = cssVar('--surface-solid') || '#fff';
  ctx.lineWidth = 2;
  ctx.stroke();
}

function hexToRgba(color, alpha) {
  const hex = color.trim();
  const match = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(hex);
  if (!match) return `rgba(79, 154, 72, ${alpha})`;
  let value = match[1];
  if (value.length === 3) value = value.split('').map((c) => c + c).join('');
  const int = parseInt(value, 16);
  const r = (int >> 16) & 255;
  const g = (int >> 8) & 255;
  const b = int & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function renderCharts() {
  const h = state.history;
  const water = cssVar('--water') || '#3a9bd9';
  const sun = cssVar('--sun') || '#e5a72c';
  const accent = cssVar('--accent') || '#4f9a48';

  drawChart($('#chart-moisture'), h.moisture, { min: 0, max: 100, target: state.target, color: water });
  drawChart($('#chart-moisture-2'), h.moisture, { min: 0, max: 100, target: state.target, color: water });
  drawChart($('#chart-light'), h.light, { min: 0, max: 40000, color: sun });

  const sparkConfig = {
    temperature: { color: sun, min: 10, max: 45 },
    moisture: { color: water, min: 0, max: 100 },
    light: { color: sun, min: 0, max: 40000 },
    tank: { color: accent, min: 0, max: 100 }
  };

  $$('[data-spark]').forEach((canvas) => {
    const key = canvas.dataset.spark;
    const config = sparkConfig[key];
    drawChart(canvas, h[key], { ...config, target: undefined });
  });
}

function renderConn() {
  const pill = $('#conn-pill');
  const text = $('#conn-text');
  if (!pill || !text) return;
  pill.classList.toggle('online', state.online);
  if (!state.online) {
    text.textContent = 'Автономный режим';
  } else {
    text.textContent = state.source === 'arduino' ? 'Сервер · Arduino' : 'Сервер · эмулятор';
  }
}

function render() {
  bindValues();
  bindInputs();
  renderSwitches();
  renderGauge();
  renderExtras();
  renderZones();
  renderLogs();
  renderConn();
  renderCharts();
}

/* ---------------------------------- тосты --------------------------------- */

function toast(message, type = 'info') {
  const host = $('#toasts');
  if (!host) return;
  const node = document.createElement('div');
  node.className = `toast ${type === 'info' ? '' : type}`;
  node.textContent = message;
  host.appendChild(node);
  setTimeout(() => {
    node.classList.add('out');
    setTimeout(() => node.remove(), 320);
  }, 2600);
}

/* ------------------------------ действия UI ------------------------------- */

function setDevice(device, isOn, { silent = false, seconds = 0 } = {}) {
  setPath(state, `devices.${device}.on`, isOn);
  if (state.zones.length) {
    state.zones.forEach((zone) => {
      zone.devices[device].on = isOn;
      zone.devices[device].remaining = isOn && seconds ? Number(seconds) : 0;
    });
  }
  if (state.online) postJSON('/api/devices', { zone_id: 0, device, on: isOn, seconds: seconds || null });
  if (!silent) {
    addLog(`${deviceName(device)}: ${isOn ? 'запущено' : 'остановлено'} (все 12 участков)`);
  }
  saveState();
  render();
}

function deviceName(device) {
  return { watering: 'Полив', ventilation: 'Проветривание', lighting: 'Досветка' }[device] || device;
}

function pulseDevice(device, seconds) {
  const duration = Number.isFinite(seconds)
    ? seconds
    : device === 'watering' ? state.wateringDuration : state.ventilationDuration;

  setDevice(device, true, { seconds: duration });
  addLog(`${deviceName(device)}: ручной запуск на ${duration} с`);
  toast(`${deviceName(device)} — запуск на ${duration} с`);

  clearTimeout(pulseTimers[device]);
  pulseTimers[device] = setTimeout(() => {
    setDevice(device, false);
    toast(`${deviceName(device)} — завершено`);
  }, duration * 1000);
}

const ACTIONS = {
  toggle(event, button) { setDevice(button.dataset.device, !getPath(state, `devices.${button.dataset.device}.on`)); },
  pulse(event, button) { pulseDevice(button.dataset.device); },
  'select-zone'(event, button) {
    state.selectedZone = Number(button.dataset.zone) || 1;
    saveState();
    render();
  },
  'zone-device'(event, button) {
    const zoneId = Number(button.dataset.zone);
    const device = button.dataset.device;
    const zone = zoneById(zoneId);
    if (!zone) return;
    const isOn = !zone.devices[device].on;
    const seconds = isOn
      ? (device === 'watering' ? state.wateringDuration
        : device === 'ventilation' ? state.ventilationDuration : 0)
      : 0;
    setZoneDevice(zoneId, device, isOn, seconds);
    if (device === 'watering' && isOn) toast(`${zone.name}: полив включён`);
  },
  'install-pwa'() { installPWA(); },
  'next-mode'() {
    const order = ['auto', 'eco', 'boost', 'manual'];
    state.mode = order[(order.indexOf(state.mode) + 1) % order.length];
    applyMode();
    addLog(`Режим переключён: ${MODE_NAMES[state.mode]}`);
    toast(`Режим: ${MODE_NAMES[state.mode]}`);
    saveState();
    render();
  },
  goto(event, button) { switchView(button.dataset.view); },
  refresh() { loadRemote(true); },
  'toggle-theme'() {
    state.theme = state.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = state.theme;
    saveState();
    render();
  },
  calibrate() {
    addLog('Калибровка датчика влажности выполнена');
    toast('Датчик влажности откалиброван');
    saveState();
    render();
  },
  connect() {
    state.apiBase = ($('[data-model="apiBase"]')?.value || '').trim();
    saveState();
    loadRemote(true);
  },
  export() {
    const blob = new Blob([JSON.stringify(state, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `greenhouse-${new Date().toISOString().slice(0, 10)}.json`;
    link.click();
    URL.revokeObjectURL(url);
    toast('Данные выгружены в JSON');
  },
  reset() {
    if (!window.confirm('Сбросить настройки теплицы к заводским?')) return;
    state = clone(DEFAULTS);
    localStorage.removeItem(STORAGE_KEY);
    document.documentElement.dataset.theme = state.theme;
    addLog('Настройки сброшены к заводским');
    toast('Настройки сброшены');
    switchView('dashboard');
  },
  'filter-logs'(event, button) {
    state.logFilter = button.dataset.filter;
    saveState();
    renderLogs();
  },
  'clear-logs'() {
    state.logs = [];
    saveState();
    renderLogs();
    toast('Журнал очищен');
  }
};

function initActions() {
  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-action]');
    if (!button) return;
    const action = ACTIONS[button.dataset.action];
    if (action) action(event, button);
  });

  $$('[data-model]').forEach((input) => {
    const handler = () => {
      const path = input.dataset.model;
      let value;
      if (input.type === 'checkbox') value = input.checked;
      else if (input.type === 'range' || input.type === 'number') value = Number(input.value);
      else value = input.value;

      setPath(state, path, value);
      saveState();
      render();
    };
    input.addEventListener(input.type === 'text' ? 'change' : 'input', handler);
  });

  $('#modes').addEventListener('click', (event) => {
    const button = event.target.closest('.mode');
    if (!button) return;
    state.mode = button.dataset.mode;
    applyMode();
    addLog(`Выбран режим: ${MODE_NAMES[state.mode]}`);
    toast(`Режим: ${MODE_NAMES[state.mode]}`);
    saveState();
    render();
  });

  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(renderCharts, 150);
  });
}

function applyMode() {
  const presets = {
    auto: { target: 55, thresholds: { moisture: 35, temperature: 30, light: 8000 } },
    eco: { target: 45, thresholds: { moisture: 28, temperature: 32, light: 5000 } },
    boost: { target: 65, thresholds: { moisture: 45, temperature: 27, light: 12000 } },
    manual: null
  };
  const preset = presets[state.mode];
  if (!preset) return;
  state.target = preset.target;
  Object.assign(state.thresholds, preset.thresholds);
}

/* ---------------------------- демонстрационные данные ---------------------- */

function seedHistory() {
  Object.entries(state.history).forEach(([key, list]) => {
    if (list.length >= MAX_POINTS) return;
    const base = state.sensors[key] ?? 50;
    const max = key === 'light' ? 40000 : 100;
    const amplitude = key === 'light' ? 900 : 3;
    const filled = [];
    for (let i = MAX_POINTS - 1; i >= 0; i -= 1) {
      const wave = Math.sin((i + key.length) / 4) * amplitude;
      filled.push(round1(clamp(base + wave + (Math.random() - 0.5) * 2, 5, max)));
    }
    state.history[key] = filled.slice(-MAX_POINTS);
  });
}

function pushHistory() {
  Object.entries(state.history).forEach(([key, list]) => {
    const value = key === 'tank' ? state.tank : state.sensors[key];
    if (value == null) return;
    list.push(round1(value));
    if (list.length > MAX_POINTS) list.shift();
  });
}

function simulateLocal() {
  if (!state.zones.length) seedZones();

  const noise = (amount) => (Math.random() - 0.5) * amount;
  const hour = new Date().getHours() + new Date().getMinutes() / 60;
  const daylight = clamp(Math.sin(((hour - 6) / 12) * Math.PI), 0, 1);

  const anyWatering = state.zones.some((zone) => zone.devices.watering.on);
  const anyLighting = state.zones.some((zone) => zone.devices.lighting.on);
  const anyVentilation = state.zones.some((zone) => zone.devices.ventilation.on);
  const dayLight = daylight * 36000 + (anyLighting ? 9000 : 0);

  state.zones.forEach((zone, index) => {
    const s = zone.sensors;
    const dev = zone.devices;
    const offset = (index + 1 - 6.5) / 6.5;

    ['watering', 'ventilation', 'lighting'].forEach((name) => {
      const d = dev[name];
      if (d.on && d.remaining > 0) {
        d.remaining = round1(d.remaining - TICK_MS / 1000);
        if (d.remaining <= 0) { d.remaining = 0; d.on = false; }
      }
    });

    s.light = Math.round(clamp(dayLight + noise(800), 0, 45000));
    const comfort = 24 - (state.windowOpen / 100) * 4 - offset * 0.4 + (dev.lighting.on ? 1 : 0);
    s.temperature = round1(clamp(s.temperature + (comfort - s.temperature) * 0.15 + noise(0.25), 12, 42));
    s.moisture = round1(clamp(
      s.moisture - 0.3 + (dev.watering.on ? 1.8 : 0) - (dev.ventilation.on ? 0.3 : 0) + noise(0.3),
      5, 100
    ));
    zone.status = zoneStatus(s);
  });

  const avg = (key) => {
    const values = state.zones.map((zone) => zone.sensors[key]).filter((v) => v != null);
    return values.length ? round1(values.reduce((a, b) => a + b, 0) / values.length) : null;
  };
  state.sensors.temperature = avg('temperature');
  state.sensors.moisture = avg('moisture');
  state.sensors.light = avg('light');
  state.devices.watering.on = anyWatering;
  state.devices.ventilation.on = anyVentilation;
  state.devices.lighting.on = anyLighting;

  if (anyWatering) {
    state.tank = round1(clamp(state.tank - 0.35, 0, 100));
    if (state.tank <= 0 && !state.tankAlerted) {
      state.tankAlerted = true;
      addLog('Бак пуст — полив остановлен', 'warn');
      toast('Бак пуст: полив остановлен', 'warn');
      state.zones.forEach((zone) => { zone.devices.watering.on = false; zone.devices.watering.remaining = 0; });
      state.devices.watering.on = false;
    }
  }
  if (state.tank > 5) state.tankAlerted = false;

  state.windowOpen = anyVentilation
    ? clamp(state.windowOpen + 15, 0, 100)
    : clamp(state.windowOpen - 10, 0, 100);

  // локальная автоматика (пока нет сервера)
  if (state.mode !== 'manual') {
    state.zones.forEach((zone) => {
      const s = zone.sensors;
      if (state.auto.watering && s.moisture < state.thresholds.moisture && !zone.devices.watering.on && state.tank > 5) {
        zone.devices.watering.on = true;
        zone.devices.watering.remaining = state.wateringDuration;
        addLog(`${zone.name}: автополив (низкая влажность)`, 'warn');
      }
      if (state.auto.ventilation && s.temperature > state.thresholds.temperature && !zone.devices.ventilation.on) {
        zone.devices.ventilation.on = true;
        zone.devices.ventilation.remaining = state.ventilationDuration;
        addLog(`${zone.name}: автопроветривание (перегрев)`, 'warn');
      }
      if (state.auto.lighting) {
        const shouldGlow = s.light < state.thresholds.light;
        if (shouldGlow !== zone.devices.lighting.on) zone.devices.lighting.on = shouldGlow;
      }
    });
  }
}

function tick() {
  const countdown = (zone) => {
    ['watering', 'ventilation', 'lighting'].forEach((name) => {
      const d = zone.devices[name];
      if (d.on && d.remaining > 0) d.remaining = Math.max(0, round1(d.remaining - TICK_MS / 1000));
    });
  };

  if (state.online) {
    state.zones.forEach(countdown); // сервер прислал данные, локально только таймеры
  } else {
    simulateLocal();
  }

  pushHistory();
  saveState();
  render();
}

/* ------------------------------ связь с сервером -------------------------- */

async function loadRemote(notify = false) {
  const base = (state.apiBase || '').replace(/\/$/, '');
  const onHttp = location.protocol === 'http:' || location.protocol === 'https:';
  const url = base ? `${base}/api/state` : (onHttp ? '/api/state' : null);

  if (!url) {
    state.online = false;
    if (notify) toast('Укажите адрес API в разделе «Режим»', 'warn');
    render();
    return;
  }

  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 3000);
    const response = await fetch(url, { signal: controller.signal });
    clearTimeout(timer);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const data = await response.json();
    const wasOffline = !state.online;
    state.online = true;
    state.source = data.source || 'arduino';

    if (data.sensors) Object.assign(state.sensors, data.sensors);
    if (typeof data.tank === 'number') state.tank = data.tank;
    if (typeof data.window_open === 'number') state.windowOpen = data.window_open;
    if (data.mode) state.mode = data.mode;

    if (data.settings) {
      const st = data.settings;
      state.target = st.moisture_target ?? state.target;
      state.thresholds.moisture = st.moisture_threshold ?? state.thresholds.moisture;
      state.thresholds.temperature = st.temperature_threshold ?? state.thresholds.temperature;
      state.thresholds.light = st.light_threshold ?? state.thresholds.light;
      state.photoperiod = st.photoperiod ?? state.photoperiod;
      state.wateringDuration = st.watering_duration ?? state.wateringDuration;
      state.ventilationDuration = st.ventilation_duration ?? state.ventilationDuration;
      if (st.auto_watering != null) state.auto.watering = Boolean(st.auto_watering);
      if (st.auto_ventilation != null) state.auto.ventilation = Boolean(st.auto_ventilation);
      if (st.auto_lighting != null) state.auto.lighting = Boolean(st.auto_lighting);
    }

    if (Array.isArray(data.zones) && data.zones.length) {
      state.zones = data.zones.map((zone) => ({
        id: zone.id,
        name: zone.name,
        sensors: { ...zone.sensors },
        devices: {
          watering: { on: !!zone.devices?.watering?.on, remaining: zone.devices?.watering?.remaining || 0 },
          ventilation: { on: !!zone.devices?.ventilation?.on, remaining: zone.devices?.ventilation?.remaining || 0 },
          lighting: { on: !!zone.devices?.lighting?.on, remaining: zone.devices?.lighting?.remaining || 0 }
        },
        target: zone.target ?? state.target,
        status: zone.status || 'ok'
      }));
    } else if (!state.zones.length) {
      seedZones();
    }

    if (data.devices) {
      Object.entries(data.devices).forEach(([device, value]) => {
        if (state.devices[device]) state.devices[device].on = Boolean(value.on ?? value);
      });
    }

    if (notify || wasOffline) {
      toast(`Сервер теплицы на связи (${state.source === 'arduino' ? 'Arduino' : 'эмулятор'})`);
      try {
        const logsResp = await fetch(`${base}/api/logs?limit=40`);
        if (logsResp.ok) {
          const logsData = await logsResp.json();
          state.logs = (logsData.logs || []).map((entry) => ({
            t: entry.ts, level: entry.level, msg: entry.message
          }));
        }
      } catch (error) {
        /* журнал не критичен */
      }
    }
  } catch (error) {
    state.online = false;
    if (notify) toast(`Сервер недоступен (${error.name === 'AbortError' ? 'таймаут' : error.message}). Демо-режим.`, 'warn');
  }
  saveState();
  render();
}

/* ---------------------------------- старт --------------------------------- */

function initClock() {
  const node = $('#clock');
  if (!node) return;
  const update = () => {
    node.textContent = new Date().toLocaleString('ru-RU', {
      day: '2-digit', month: 'long', hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
  };
  update();
  setInterval(update, 1000);
}

function init() {
  document.documentElement.dataset.theme = state.theme;

  if (!state.zones.length) seedZones();
  seedHistory();
  if (!state.logs.length) {
    addLog('Панель управления запущена');
    addLog('Теплица из 12 участков инициализирована');
  }

  initRouter();
  initActions();
  initClock();
  initPWA();

  setInterval(tick, TICK_MS);
  setInterval(() => loadRemote(false), TICK_MS);
  loadRemote(false);
}

/* ----------------------------------- PWA ---------------------------------- */

async function initPWA() {
  const onHttp = location.protocol === 'http:' || location.protocol === 'https:';
  if ('serviceWorker' in navigator && onHttp) {
    try {
      await navigator.serviceWorker.register('service-worker.js');
    } catch (error) {
      console.warn('Service worker не зарегистрирован:', error);
    }
  }

  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault();
    deferredPrompt = event;
    const button = $('#pwa-install');
    if (button) button.hidden = false;
  });

  window.addEventListener('appinstalled', () => {
    deferredPrompt = null;
    const button = $('#pwa-install');
    if (button) button.hidden = true;
    toast('Приложение установлено на устройство');
  });

  const standalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone;
  if (standalone) document.body.classList.add('pwa-standalone');

  const button = $('#pwa-install');
  if (button && !deferredPrompt) button.hidden = true;
}

async function installPWA() {
  if (!deferredPrompt) {
    toast('Откройте панель в браузере телефона и выберите «Добавить на экран»', 'warn');
    return;
  }
  deferredPrompt.prompt();
  const choice = await deferredPrompt.userChoice;
  if (choice && choice.outcome === 'accepted') toast('Устанавливаем приложение…');
  deferredPrompt = null;
  const button = $('#pwa-install');
  if (button) button.hidden = true;
}

document.addEventListener('DOMContentLoaded', init);
