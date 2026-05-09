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

  // Media picker modal -------------------------------------------------------
  // Any [data-madga-featured] block exposes Choose / Change / Clear actions.
  // The picker URL is /studio/media/picker/ and we load it into a portal
  // backdrop on demand. Selection sets a hidden input + updates preview.
  const PICKER_URL = '/studio/media/picker/';
  let activePickerOwner = null;

  function openPicker(ownerEl) {
    activePickerOwner = ownerEl;
    const portal = document.querySelector('[data-madga-mp-portal]');
    if (!portal) return;
    fetch(PICKER_URL, {credentials: 'same-origin'})
      .then(r => r.text())
      .then(html => {
        portal.innerHTML = html;
        portal.hidden = false;
        if (window.htmx) window.htmx.process(portal);
        const input = portal.querySelector('input[type=search]');
        if (input) input.focus();
      });
  }
  function closePicker() {
    const portal = document.querySelector('[data-madga-mp-portal]');
    if (!portal) return;
    portal.hidden = true;
    portal.innerHTML = '';
    activePickerOwner = null;
  }
  function applyPickToFeatured(owner, pick) {
    const input = owner.querySelector('[data-fi-input]');
    const preview = owner.querySelector('[data-fi-preview]');
    const img = owner.querySelector('[data-fi-img]');
    const empty = owner.querySelector('[data-fi-pick].madga-fi-empty');
    const actions = owner.querySelector('[data-fi-actions]');
    const filenameSpan = owner.querySelector('[data-fi-filename]');
    if (input) input.value = pick.id;
    if (img) { img.src = pick.url; img.alt = pick.alt || ''; }
    if (preview) preview.hidden = false;
    if (empty) empty.hidden = true;
    if (actions) actions.hidden = false;
    if (filenameSpan) filenameSpan.textContent = pick.filename || '';
  }
  function clearFeatured(owner) {
    const input = owner.querySelector('[data-fi-input]');
    const preview = owner.querySelector('[data-fi-preview]');
    const empty = owner.querySelector('[data-fi-pick].madga-fi-empty');
    const actions = owner.querySelector('[data-fi-actions]');
    if (input) input.value = '';
    if (preview) preview.hidden = true;
    if (empty) empty.hidden = false;
    if (actions) actions.hidden = true;
  }

  document.addEventListener('click', function (e) {
    // Open picker
    const pickBtn = e.target.closest('[data-fi-pick]');
    if (pickBtn) {
      const owner = pickBtn.closest('[data-madga-featured]');
      if (owner) openPicker(owner);
      return;
    }
    // Clear featured
    const clearBtn = e.target.closest('[data-fi-clear]');
    if (clearBtn) {
      const owner = clearBtn.closest('[data-madga-featured]');
      if (owner) clearFeatured(owner);
      return;
    }
    // Close picker (X button or backdrop click outside the modal box)
    if (e.target.closest('[data-madga-mp-close]')) { closePicker(); return; }
    if (e.target.matches('[data-madga-mp-portal]')) { closePicker(); return; }
    // Pick selection
    const tile = e.target.closest('[data-madga-pick]');
    if (tile && activePickerOwner) {
      applyPickToFeatured(activePickerOwner, {
        id: tile.dataset.pickId,
        url: tile.dataset.pickUrl,
        alt: tile.dataset.pickAlt,
        filename: tile.dataset.pickFilename,
        width: parseInt(tile.dataset.pickWidth || '0', 10),
        height: parseInt(tile.dataset.pickHeight || '0', 10),
      });
      closePicker();
    }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closePicker();
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

  // Toast auto-dismiss -------------------------------------------------------
  function dismissToast(toast) {
    if (!toast || toast.classList.contains('is-leaving')) return;
    toast.classList.add('is-leaving');
    setTimeout(() => toast.remove(), 250);
  }
  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-madga-toast]').forEach(t => {
      setTimeout(() => dismissToast(t), 4000);
    });
  });
  document.addEventListener('click', function (e) {
    const dismiss = e.target.closest('[data-madga-toast-dismiss]');
    if (dismiss) dismissToast(dismiss.closest('[data-madga-toast]'));
  });

  // Confirm modal ------------------------------------------------------------
  // Any element with data-madga-confirm="message" intercepts the form submit
  // and asks for confirmation. data-madga-confirm-variant changes the OK
  // button color (default, danger).
  let pendingConfirmForm = null;
  function openConfirm(message, form) {
    pendingConfirmForm = form;
    const modal = document.querySelector('[data-madga-confirm-backdrop]');
    if (!modal) { return form.submit(); }  // graceful fallback
    modal.querySelector('[data-madga-confirm-msg]').textContent = message;
    modal.hidden = false;
  }
  function closeConfirm() {
    pendingConfirmForm = null;
    const modal = document.querySelector('[data-madga-confirm-backdrop]');
    if (modal) modal.hidden = true;
  }
  document.addEventListener('submit', function (e) {
    const trigger = e.submitter && e.submitter.closest('[data-madga-confirm]');
    if (!trigger) return;
    if (trigger.dataset.madgaConfirmAcknowledged === '1') {
      delete trigger.dataset.madgaConfirmAcknowledged;
      return;
    }
    e.preventDefault();
    openConfirm(trigger.getAttribute('data-madga-confirm'), e.target);
    pendingConfirmForm._submitter = e.submitter;
  }, true);
  document.addEventListener('click', function (e) {
    if (e.target.closest('[data-madga-confirm-cancel]')) { closeConfirm(); return; }
    if (e.target.matches('[data-madga-confirm-backdrop]')) { closeConfirm(); return; }
    if (e.target.closest('[data-madga-confirm-ok]')) {
      const form = pendingConfirmForm;
      const submitter = form && form._submitter;
      closeConfirm();
      if (!form) return;
      if (submitter) {
        submitter.dataset.madgaConfirmAcknowledged = '1';
        submitter.click();
      } else {
        form.submit();
      }
    }
  });
})();
