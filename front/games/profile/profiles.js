/* Аватары игроков в комнатах AmrGames.
 *
 * Профили участников подтягиваются одним запросом /api/profiles?ids=…,
 * поэтому в списках комнат, на досках и в итогах видно настоящий аватар
 * игрока, а не только инициалы. Если аватара нет — рисуем инициалы на цвете
 * профиля (или на подобранном из ника цвете).
 *
 * Кэш живёт в памяти страницы; аватары общие для всех игр AmrGames.
 * Аватар и имя кликабельны и открывают профиль игрока — адрес страницы
 * профиля берётся из src самого этого скрипта, поэтому ссылка работает
 * и на домене игр, и в локальной разработке без настройки каждой страницы.
 */
(function () {
  'use strict';

  const CONN_KEY = 'greenhouse.games.conn.v1';
  const PANEL_KEY = 'greenhouse.state.v1';
  const COLORS = ['#7a5c3e', '#3f6f5a', '#6b4a7a', '#8a4a3a', '#4a5f8a', '#6f6a3a'];
  const MAX_IDS = 60;

  const byId = new Map();
  const byName = new Map();
  let pending = null;
  let queued = [];

  /* Страница профиля лежит рядом со скриптом: <каталог игр>/profile/. */
  const PROFILE_PAGE = (function () {
    const script = document.currentScript;
    const src = script && script.src ? script.src : '';
    return src ? src.replace(/[^/]*$/, '') : '../profile/';
  })();

  function readJson(key) {
    try {
      const value = JSON.parse(localStorage.getItem(key) || 'null');
      return value && typeof value === 'object' ? value : null;
    } catch (error) {
      return null;
    }
  }

  function apiBase() {
    const own = readJson(CONN_KEY) || {};
    const panel = readJson(PANEL_KEY) || {};
    return String(own.apiBase || panel.apiBase || '').trim().replace(/\/+$/, '');
  }

  function remember(profiles) {
    (profiles || []).forEach((profile) => {
      if (!profile || profile.id == null) return;
      const id = Number(profile.id);
      byId.set(id, profile);
      if (profile.username) byName.set(String(profile.username).toLowerCase(), profile);
    });
  }

  /* Собирает неизвестные id и грузит их одним пакетом. Повторные вызовы во
     время загрузки добавляются в очередь и уходят следующим запросом. */
  function ensure(players) {
    const ids = [];
    (players || []).forEach((player) => {
      const id = player && player.id != null ? Number(player.id) : 0;
      if (id && !byId.has(id) && ids.indexOf(id) === -1) ids.push(id);
    });
    if (ids.length) queued = queued.concat(ids).slice(0, MAX_IDS);
    if (!queued.length) return Promise.resolve(false);
    return pending || flush();
  }

  function flush() {
    const batch = queued.splice(0, MAX_IDS);
    const url = apiBase() + '/api/profiles?ids=' + batch.join(',');
    pending = fetch(url, { cache: 'no-store' })
      .then((response) => (response.ok ? response.json() : { profiles: [] }))
      .then((data) => {
        const before = byId.size;
        remember(data.profiles);
        return byId.size > before;
      })
      .catch(() => false)
      .then((changed) => {
        pending = null;
        if (changed) document.dispatchEvent(new CustomEvent('amr:profiles'));
        if (queued.length) return flush();
        return changed;
      });
    return pending;
  }

  function initials(name) {
    const words = String(name || '').split(/\s+/).filter(Boolean);
    if (!words.length) return '?';
    const first = words[0].charAt(0);
    const second = words.length > 1 ? words[1].charAt(0) : (words[0].charAt(1) || '');
    return (first + second).toUpperCase();
  }

  function colorFor(name) {
    let hash = 0;
    for (const char of String(name || '')) hash = (hash * 31 + char.charCodeAt(0)) % 9973;
    return COLORS[hash % COLORS.length];
  }

  function find(id, name) {
    if (id != null) {
      const profile = byId.get(Number(id));
      if (profile) return profile;
    }
    const key = String(name || '').toLowerCase();
    return key ? (byName.get(key) || null) : null;
  }

  function escapeHtml(text) {
    return String(text == null ? '' : text).replace(/[&<>"']/g, (char) => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]
    ));
  }

  /* Ссылка на страницу профиля игрока: пустая, пока профиль не загружен. */
  function url(id, name) {
    const profile = find(id, name);
    if (!profile || !profile.username) return '';
    return PROFILE_PAGE + '?u=' + encodeURIComponent(String(profile.username));
  }

  /* Аватар, по клику открывающий профиль игрока, — в новой вкладке, чтобы
     не терять комнату и партию. Ободок профиля (если выбран) рисуется
     кольцом вокруг аватара. */
  function html(id, name, extra) {
    const profile = find(id, name);
    const image = profile && profile.avatar_url ? apiBase() + profile.avatar_url : '';
    const color = (profile && profile.accent) || colorFor(name);
    const inner = image
      ? '<img src="' + escapeHtml(image) + '" alt="" loading="lazy">'
      : escapeHtml(initials(name));
    const avatar = '<span class="amr-avatar' + (extra ? ' ' + extra : '') + '" style="background:'
      + escapeHtml(color) + '">' + inner + '</span>';
    const frame = String((profile && profile.frame) || '').trim();
    const body = frame
      ? '<span class="amr-frame" data-frame="' + escapeHtml(frame) + '">' + avatar + '</span>'
      : avatar;
    const href = url(id, name);
    if (!href) return body;
    return '<a class="amr-avatar-link" href="' + escapeHtml(href)
      + '" target="_blank" rel="noopener" title="Открыть профиль">' + body + '</a>';
  }

  /* Имя игрока: в профиле может быть своё отображаемое имя, а само имя —
     ссылка на профиль. */
  function name(id, fallback) {
    const profile = find(id, fallback);
    return (profile && profile.display_name) || fallback || '';
  }

  /* Значок статуса: emoji или картинка-эмблема. */
  function statusImageUrl(url) {
    const value = String(url || '');
    if (value.startsWith('/games/') && !location.pathname.startsWith('/games/')) {
      return value.slice('/games'.length);
    }
    return value;
  }

  function statusIcon(view) {
    const url = statusImageUrl((view && view.icon_url) || '');
    if (url) {
      /* Без loading="lazy": списки игроков перерисовываются при каждом опросе,
         и отложенная загрузка каждый раз начиналась заново — значок мигал. */
      return '<img class="amr-status-img" src="' + escapeHtml(url) + '" alt="">';
    }
    return escapeHtml((view && view.icon) || '');
  }

  /* Статус игрока: полная плашка или только значок. Пусто, если статуса нет,
     поэтому вызывать можно где угодно, не проверяя профиль. */
  function status(id, fallback, compact) {
    const profile = find(id, fallback);
    const view = profile && profile.status_view;
    if (!view) return '';
    const full = compact === false;
    return '<span class="amr-status' + (full ? '' : ' icon-only') + '"'
      + ' style="--status-color:' + escapeHtml(view.color) + '"'
      + ' title="' + escapeHtml(view.title) + '">' + statusIcon(view)
      + (full ? ' ' + escapeHtml(view.title) : '') + '</span>';
  }

  /* Третий аргумент выключает значок статуса: в лобби статус рисуют
     отдельной плашкой справа от имени, чтобы не было двух значков. */
  function link(id, fallback, withBadge) {
    const profile = find(id, fallback);
    const label = escapeHtml(name(id, fallback));
    const view = withBadge === false ? null : (profile && profile.status_view);
    const badge = view
      ? ' <span class="amr-status icon-only" style="--status-color:' + escapeHtml(view.color)
        + '" title="' + escapeHtml(view.title) + '">' + statusIcon(view) + '</span>'
      : '';
    const href = url(id, fallback);
    if (!href) return label + badge;
    return '<a class="amr-name" href="' + escapeHtml(href)
      + '" target="_blank" rel="noopener" title="Открыть профиль">' + label + '</a>' + badge;
  }

  window.AmrProfiles = {
    ensure: ensure, html: html, name: name, link: link, url: url,
    status: status, find: find, remember: remember
  };
})();
