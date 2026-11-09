/* Блок профиля в шапке страниц AmrGames: аватар, имя и переход в профиль.
 *
 * Данные берутся из того же localStorage, что и у страниц игр
 * (greenhouse.auth.v1), поэтому вход, сделанный в игре, сразу виден на витрине
 * и наоборот. Адрес API — из настроек подключения страниц игр или панели:
 * пустой адрес значит «тот же домен», то есть /api/ текущего сайта.
 */
(function () {
  'use strict';

  const AUTH_KEY = 'greenhouse.auth.v1';
  const CONN_KEY = 'greenhouse.games.conn.v1';
  const PANEL_KEY = 'greenhouse.state.v1';

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

  function avatarUrl(user) {
    if (!user || !user.id || !user.avatar_url) return '';
    return apiBase() + user.avatar_url;
  }

  /* Эмблема статуса: на витрине profile лежит в /profile, на панели — в
     /games/profile, поэтому префикс /games убираем только вне панели. */
  function statusIconUrl(url) {
    const value = String(url || '');
    if (value.startsWith('/games/') && !location.pathname.startsWith('/games/')) {
      return value.slice('/games'.length);
    }
    return value;
  }

  function initials(name) {
    const text = String(name || '').trim();
    return text ? text.slice(0, 1).toUpperCase() : '👤';
  }

  function currentUser() {
    const saved = readJson(AUTH_KEY);
    return saved && saved.token ? (saved.user || {}) : null;
  }

  /* Аватар в пилюле оборачивается в ободок профиля. Страницы кладут картинку
     и запасной значок прямо в пилюлю, поэтому обёртку создаём сами — и только
     один раз, чтобы повторная отрисовка не плодила вложенность. */
  function frameWrap(pill) {
    let wrapper = null;
    for (const child of pill.children) {
      if (child.classList && child.classList.contains('amr-frame')) { wrapper = child; break; }
    }
    if (wrapper) return wrapper;
    const image = document.getElementById('user-avatar');
    const fallback = document.getElementById('user-avatar-fallback');
    const anchor = image || fallback;
    if (!anchor || !anchor.parentNode) return null;
    wrapper = document.createElement('span');
    wrapper.className = 'amr-frame';
    anchor.parentNode.insertBefore(wrapper, anchor);
    if (image) wrapper.appendChild(image);
    if (fallback) wrapper.appendChild(fallback);
    return wrapper;
  }

  /* Значок статуса рядом с ником. Подпись и цвет приходят с профилем
     (поле status_view), поэтому справочник статусов здесь не нужен. */
  function statusNode(pill) {
    let node = document.getElementById('user-status');
    if (node) return node;
    const name = document.getElementById('user-name');
    if (!name || !name.parentNode) return null;
    node = document.createElement('span');
    node.id = 'user-status';
    node.className = 'amr-status icon-only';
    node.hidden = true;
    name.parentNode.insertBefore(node, name.nextSibling);
    return node;
  }

  function render(user) {
    const pill = document.getElementById('user-pill');
    if (!pill) return;
    const name = user ? String(user.display_name || user.username || '').trim() : '';
    const loginLink = document.getElementById('login-link');
    pill.hidden = !name;
    if (loginLink) loginLink.hidden = Boolean(name);
    if (!name) return;

    const nameNode = document.getElementById('user-name');
    if (nameNode) nameNode.textContent = name;

    /* Статус открывается достижениями и показывается значком с подсказкой. */
    const status = statusNode(pill);
    const view = user && user.status_view;
    if (status) {
      status.hidden = !view;
      if (view) {
        status.style.setProperty('--status-color', String(view.color || ''));
        /* Значок пересобираем только когда он правда сменился: новый <img> с тем
           же src браузер загружает заново, и эмблема «моргает» на каждом опросе. */
        const url = view.icon_url ? statusIconUrl(view.icon_url) : '';
        const badge = status.querySelector('img.amr-status-img');
        if (url) {
          if (!badge || badge.getAttribute('src') !== url) {
            status.textContent = '';
            const image = document.createElement('img');
            image.className = 'amr-status-img';
            image.src = url;
            image.alt = '';
            status.appendChild(image);
          }
        } else if (badge || status.textContent !== String(view.icon || '')) {
          status.textContent = String(view.icon || '');
        }
        status.title = String(view.title || '');
      }
    }

    const url = avatarUrl(user);
    const image = document.getElementById('user-avatar');
    const fallback = document.getElementById('user-avatar-fallback');
    if (image) {
      image.hidden = !url;
      if (url) image.src = url;
      else image.removeAttribute('src');
    }
    if (fallback) {
      fallback.hidden = Boolean(url);
      fallback.textContent = initials(name);
    }

    /* Ободок профиля вокруг аватара: пустая строка значит «без ободка». */
    const wrapper = frameWrap(pill);
    if (wrapper) wrapper.dataset.frame = String((user && user.frame) || '').trim();

    if (user && user.accent) {
      pill.style.setProperty('--profile-accent', user.accent);
      pill.dataset.accent = 'custom';
    } else {
      pill.style.removeProperty('--profile-accent');
      delete pill.dataset.accent;
    }
  }

  window.AmrProfile = { render: render, current: currentUser, avatarUrl: avatarUrl };

  document.addEventListener('DOMContentLoaded', function () {
    render(currentUser());
    window.addEventListener('storage', function (event) {
      if (event.key === AUTH_KEY) render(currentUser());
    });
  });
})();
