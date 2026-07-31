/* ═══════════════════════════════════════════
   VoidOnyx — Main JS
   Geo-redirect, animations, UI interactions
═══════════════════════════════════════════ */

(function () {
  'use strict';

  /* ── 1. INDIA GEO-REDIRECT ──────────────────────────── */
  function checkIndiaRedirect() {
    // Only run on voidonyx.com (not .in)
    const host = window.location.hostname;
    if (host !== 'voidonyx.com' && host !== 'www.voidonyx.com') return;

    try {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || '';
      const lang = navigator.language || navigator.userLanguage || '';
      const isIndia =
        tz === 'Asia/Kolkata' ||
        tz === 'Asia/Calcutta' ||
        lang.startsWith('hi') ||       // Hindi
        lang.startsWith('bn') ||       // Bengali
        lang.startsWith('mr') ||       // Marathi
        lang.startsWith('te') ||       // Telugu
        lang.startsWith('gu') ||       // Gujarati
        lang.startsWith('ta');         // Tamil

      // Respect user preference: if they manually came from .in previously
      const pref = sessionStorage.getItem('ox_region');
      if (pref === 'com') return; // User chose global, respect it

      if (isIndia) {
        window.location.replace(
          'https://voidonyx.in' + window.location.pathname + window.location.search
        );
      }
    } catch (e) {
      // Silently ignore if Intl not available
    }
  }

  /* ── 2. CURRENCY TOGGLE (for .in page) ─────────────── */
  function initCurrencyToggle() {
    const toggle = document.getElementById('currencyToggle');
    if (!toggle) return;
    const inrPrices = document.querySelectorAll('[data-inr]');
    const usdPrices = document.querySelectorAll('[data-usd]');
    let isINR = document.body.classList.contains('india-variant');

    function updatePrices() {
      inrPrices.forEach(el => { el.style.display = isINR ? '' : 'none'; });
      usdPrices.forEach(el => { el.style.display = isINR ? 'none' : ''; });
      const btns = toggle.querySelectorAll('button');
      btns.forEach(btn => btn.classList.remove('active'));
      toggle.querySelector(isINR ? '[data-cur="inr"]' : '[data-cur="usd"]').classList.add('active');
    }

    toggle.addEventListener('click', function (e) {
      const btn = e.target.closest('[data-cur]');
      if (!btn) return;
      isINR = btn.dataset.cur === 'inr';
      updatePrices();
    });

    updatePrices();
  }

  /* ── 3. STICKY NAV SCROLL ───────────────────────────── */
  function initNav() {
    const nav = document.querySelector('.ox-nav');
    if (!nav) return;
    window.addEventListener('scroll', function () {
      nav.classList.toggle('scrolled', window.scrollY > 20);
    }, { passive: true });
  }

  /* ── 4. MOBILE MENU ─────────────────────────────────── */
  function initMobileMenu() {
    const hamburger = document.getElementById('oxHamburger');
    const menu = document.getElementById('oxMobileMenu');
    if (!hamburger || !menu) return;
    hamburger.addEventListener('click', function () {
      menu.classList.toggle('open');
      const spans = hamburger.querySelectorAll('span');
      hamburger.classList.toggle('active');
    });
    // Close on link click
    menu.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function () {
        menu.classList.remove('open');
        hamburger.classList.remove('active');
      });
    });
  }

  /* ── 5. INTERSECTION OBSERVER (fade-in animations) ─── */
  function initFadeIn() {
    const els = document.querySelectorAll('.ox-fadein, .ox-product-card, .ox-stat-block, .ox-feature-item, .ox-price-card');
    if (!('IntersectionObserver' in window)) {
      els.forEach(el => el.style.opacity = '1');
      return;
    }
    const io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });

    els.forEach(function (el, i) {
      if (!el.classList.contains('ox-fadein')) {
        el.style.opacity = '0';
        el.style.transform = 'translateY(16px)';
        el.style.transition = `opacity 0.5s ease ${i * 0.06}s, transform 0.5s ease ${i * 0.06}s`;
      }
      io.observe(el);
    });
  }

  /* ── 6. ANIMATED COUNTERS ───────────────────────────── */
  function initCounters() {
    const counters = document.querySelectorAll('[data-counter]');
    if (!counters.length) return;
    const io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          const el = entry.target;
          const target = parseFloat(el.dataset.counter);
          const suffix = el.dataset.suffix || '';
          const prefix = el.dataset.prefix || '';
          const duration = 1600;
          const start = performance.now();
          function update(now) {
            const progress = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            const value = target < 10 ? (eased * target).toFixed(1) : Math.round(eased * target);
            el.textContent = prefix + value + suffix;
            if (progress < 1) requestAnimationFrame(update);
          }
          requestAnimationFrame(update);
          io.unobserve(el);
        }
      });
    }, { threshold: 0.3 });
    counters.forEach(el => io.observe(el));
  }

  /* ── 7. DISMISS ANNOUNCE BAR ────────────────────────── */
  function initAnnounceBar() {
    const bar = document.getElementById('oxAnnounceBar');
    const closeBtn = document.getElementById('oxAnnounceClose');
    if (!bar || !closeBtn) return;
    const key = 'ox_announce_dismissed';
    if (sessionStorage.getItem(key)) { bar.style.display = 'none'; return; }
    closeBtn.addEventListener('click', function () {
      bar.style.display = 'none';
      sessionStorage.setItem(key, '1');
    });
  }

  /* ── INIT ───────────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', function () {
    checkIndiaRedirect();
    initCurrencyToggle();
    initNav();
    initMobileMenu();
    initFadeIn();
    initCounters();
    initAnnounceBar();
  });

})();
