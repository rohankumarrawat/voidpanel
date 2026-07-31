/**
 * VoidOnyx UI Script v1.0
 * Handles: mega-menu, mobile nav, scroll effects, stat counters, currency toggle
 */

(function () {
  'use strict';

  /* ── Mega Menu (hover + click, viewport-safe) ───────────────────────────── */
  document.querySelectorAll('.ox-nav-drop-wrap').forEach(function (wrap) {
    var trigger = wrap.querySelector('.ox-nav-drop-trigger');
    var menu    = wrap.querySelector('.ox-mega-menu');
    if (!trigger || !menu) return;

    var closeTimer = null;

    function openMenu() {
      clearTimeout(closeTimer);
      // Close others
      document.querySelectorAll('.ox-nav-drop-wrap.open').forEach(function (w) {
        if (w !== wrap) w.classList.remove('open');
      });
      wrap.classList.add('open');

      // Viewport clamp — push left if right edge overflows
      requestAnimationFrame(function () {
        var rect   = menu.getBoundingClientRect();
        var overflowRight = rect.right - (window.innerWidth - 12);
        if (overflowRight > 0) {
          menu.style.left = (-overflowRight) + 'px';
        } else {
          menu.style.left = '0';
        }
      });
    }

    function scheduleClose() {
      closeTimer = setTimeout(function () { wrap.classList.remove('open'); }, 200);
    }

    // Hover intent
    trigger.addEventListener('mouseenter', openMenu);
    trigger.addEventListener('mouseleave', scheduleClose);
    menu.addEventListener('mouseenter',    function () { clearTimeout(closeTimer); });
    menu.addEventListener('mouseleave',    scheduleClose);

    // Click toggle (mobile / keyboard)
    trigger.addEventListener('click', function (e) {
      e.stopPropagation();
      if (wrap.classList.contains('open')) { wrap.classList.remove('open'); } else { openMenu(); }
    });
  });

  document.addEventListener('click', function () {
    document.querySelectorAll('.ox-nav-drop-wrap.open').forEach(function (w) { w.classList.remove('open'); });
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      document.querySelectorAll('.ox-nav-drop-wrap.open').forEach(function (w) { w.classList.remove('open'); });
    }
  });

  /* ── Mobile Hamburger ───────────────────────────────────────────────────── */
  var hamburger = document.getElementById('oxHamburger');
  var mobileMenu = document.getElementById('oxMobileMenu');
  if (hamburger && mobileMenu) {
    hamburger.addEventListener('click', function () {
      mobileMenu.classList.toggle('open');
      hamburger.classList.toggle('active');
    });
  }

  /* ── Announce bar close ─────────────────────────────────────────────────── */
  var announceClose = document.getElementById('oxAnnounceClose');
  var announceBar = document.getElementById('oxAnnounceBar');
  if (announceClose && announceBar) {
    announceClose.addEventListener('click', function () {
      announceBar.style.display = 'none';
      try { sessionStorage.setItem('ox_announce_hidden', '1'); } catch (e) {}
    });
    try {
      if (sessionStorage.getItem('ox_announce_hidden') === '1') {
        announceBar.style.display = 'none';
      }
    } catch (e) {}
  }

  /* ── Sticky Nav scroll shadow ───────────────────────────────────────────── */
  var nav = document.querySelector('.ox-nav');
  if (nav) {
    window.addEventListener('scroll', function () {
      if (window.scrollY > 10) {
        nav.style.boxShadow = '0 4px 24px rgba(15,23,42,0.08)';
      } else {
        nav.style.boxShadow = '0 1px 2px rgba(15,23,42,0.05)';
      }
    }, { passive: true });
  }

  /* ── Stat Counters ──────────────────────────────────────────────────────── */
  function animateCounter(el) {
    var target = parseFloat(el.dataset.target || '0');
    var suffix = el.dataset.suffix || '';
    var isFloat = target !== Math.floor(target);
    var duration = 1400;
    var start = null;

    function step(ts) {
      if (!start) start = ts;
      var progress = Math.min((ts - start) / duration, 1);
      var ease = 1 - Math.pow(1 - progress, 3);
      var current = target * ease;
      el.textContent = (isFloat ? current.toFixed(1) : Math.floor(current)) + suffix;
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  var counterEls = document.querySelectorAll('.ox-stat-num[data-target]');
  if (counterEls.length) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          animateCounter(entry.target);
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.3 });
    counterEls.forEach(function (el) { observer.observe(el); });
  }

  /* ── Scroll Reveal ──────────────────────────────────────────────────────── */
  var revealEls = document.querySelectorAll('.ox-reveal');
  if (revealEls.length) {
    var revealObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('ox-fadein');
          revealObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -48px 0px' });
    revealEls.forEach(function (el) { revealObserver.observe(el); });
  }

  /* ── Currency Toggle (USD ↔ INR) ────────────────────────────────────────── */
  var currToggle = document.getElementById('oxCurrencyToggle');
  if (currToggle) {
    currToggle.querySelectorAll('button').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var cur = this.dataset.currency;
        currToggle.querySelectorAll('button').forEach(function (b) { b.classList.remove('active'); });
        this.classList.add('active');
        document.querySelectorAll('[data-usd]').forEach(function (el) {
          el.textContent = cur === 'inr' ? el.dataset.inr : el.dataset.usd;
        });
      });
    });
  }

  /* ── India Geo-redirect ─────────────────────────────────────────────────── */
  (function doGeoRedirect() {
    // Only run on voidonyx.com, not .in or localhost
    if (window.location.hostname.endsWith('.in')) return;
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') return;
    try {
      if (sessionStorage.getItem('ox_region') === 'in') return;
      var tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      var lang = navigator.language || '';
      if (tz === 'Asia/Kolkata' || lang.startsWith('hi') || lang.startsWith('bn') || lang.startsWith('mr')) {
        sessionStorage.setItem('ox_region', 'in');
        window.location.replace('https://voidonyx.in' + window.location.pathname);
      }
    } catch (e) {}
  })();

})();
