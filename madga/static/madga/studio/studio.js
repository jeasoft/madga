/* MADGA Studio — minimal client-side glue.
 * Theme toggle, bulk-bar visibility on tables, autosave coordinator (used by
 * the editor templates).
 */
(function () {
  'use strict';

  // Theme toggle (light/dark) ------------------------------------------------
  const STORAGE_KEY = 'madga.theme';
  function applyTheme(t) {
    document.documentElement.setAttribute('data-theme', t);
    try { localStorage.setItem(STORAGE_KEY, t); } catch (_) {}
  }
  // Initial: prefer localStorage, fall back to current attribute or dark.
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) applyTheme(saved);
  } catch (_) {}

  document.addEventListener('click', function (e) {
    const btn = e.target.closest('[data-madga-theme-toggle]');
    if (!btn) return;
    const cur = document.documentElement.getAttribute('data-theme') || 'dark';
    applyTheme(cur === 'dark' ? 'light' : 'dark');
  });

  // Mobile sidebar drawer ----------------------------------------------------
  function setSidebar(state) {
    const app = document.querySelector('.madga-app');
    if (app) app.setAttribute('data-sidebar-state', state);
  }
  document.addEventListener('click', function (e) {
    if (e.target.closest('[data-madga-sidebar-toggle]')) {
      const app = document.querySelector('.madga-app');
      const cur = app && app.getAttribute('data-sidebar-state');
      setSidebar(cur === 'open' ? 'closed' : 'open');
      return;
    }
    if (e.target.closest('[data-madga-sidebar-close]')) {
      setSidebar('closed');
      return;
    }
    // Tap a nav link inside the drawer → close it on mobile.
    if (window.matchMedia('(max-width: 900px)').matches &&
        e.target.closest('.madga-sidebar a.madga-nav-item')) {
      setSidebar('closed');
    }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      setSidebar('closed');
      document.querySelectorAll('[data-madga-popover]:not([hidden])').forEach(p => p.hidden = true);
    }
    // ⌘K / Ctrl+K → focus topbar search
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      const input = document.querySelector('[data-madga-search]');
      if (input) { e.preventDefault(); input.focus(); input.select(); }
    }
  });

  // Topbar popovers (notifications, help) ------------------------------------
  function closeAllPopovers(except) {
    document.querySelectorAll('[data-madga-popover]').forEach(p => {
      if (p !== except) p.hidden = true;
    });
  }
  document.addEventListener('click', function (e) {
    const trigger = e.target.closest('[data-madga-popover-toggle]');
    if (trigger) {
      const key = trigger.getAttribute('data-madga-popover-toggle');
      const panel = document.querySelector('[data-madga-popover="' + key + '"]');
      if (!panel) return;
      const willOpen = panel.hidden;
      closeAllPopovers(panel);
      panel.hidden = !willOpen;
      return;
    }
    // Click outside any popover → close.
    if (!e.target.closest('[data-madga-popover]')) closeAllPopovers(null);
  });

  // Bulk-bar visibility (Posts list, etc.) -----------------------------------
  function refreshBulkBar() {
    document.querySelectorAll('[data-madga-bulk-bar]').forEach(function (bar) {
      const formId = bar.getAttribute('data-madga-bulk-bar');
      const checks = document.querySelectorAll('input[type=checkbox][form="' + formId + '"][name="ids"]:checked');
      const count = checks.length;
      bar.hidden = count === 0;
      const counter = bar.querySelector('[data-madga-bulk-count]');
      if (counter) counter.textContent = count + ' seleccionado' + (count === 1 ? '' : 's');
    });
  }
  document.addEventListener('change', function (e) {
    const t = e.target;
    if (!t || t.type !== 'checkbox') return;
    if (t.matches('[data-madga-select-all]')) {
      const formId = t.getAttribute('form') || '';
      document.querySelectorAll('input[type=checkbox][form="' + formId + '"][name="ids"]').forEach(function (c) {
        c.checked = t.checked;
      });
    }
    if (t.matches('input[name="ids"]') || t.matches('[data-madga-select-all]')) {
      refreshBulkBar();
    }
  });
  document.addEventListener('DOMContentLoaded', refreshBulkBar);
})();
