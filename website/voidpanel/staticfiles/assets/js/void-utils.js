/* VoidPanel scroll reveal + counter animation utility */
(function () {
  'use strict';

  /* ── Scroll Reveal ────────────────────────────────────────── */
  function initReveal() {
    const els = document.querySelectorAll('.reveal, .reveal-left, .reveal-right');
    if (!els.length) return;

    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry, i) => {
          if (entry.isIntersecting) {
            // Stagger children by 60ms each
            const delay = entry.target.dataset.delay ? parseInt(entry.target.dataset.delay) : 0;
            setTimeout(() => entry.target.classList.add('visible'), delay);
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
    );
    els.forEach(el => io.observe(el));
  }

  /* ── Animated Number Counters ─────────────────────────────── */
  function initCounters() {
    const counters = document.querySelectorAll('[data-count]');
    if (!counters.length) return;

    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (!entry.isIntersecting) return;
          const el = entry.target;
          const target = parseFloat(el.dataset.count);
          const suffix = el.dataset.suffix || '';
          const prefix = el.dataset.prefix || '';
          const duration = parseInt(el.dataset.duration || '1800');
          const decimals = (el.dataset.count.includes('.')) ? 1 : 0;
          const start = performance.now();

          function tick(now) {
            const elapsed = now - start;
            const progress = Math.min(elapsed / duration, 1);
            // Ease out cubic
            const eased = 1 - Math.pow(1 - progress, 3);
            const value = (target * eased).toFixed(decimals);
            el.textContent = prefix + value + suffix;
            if (progress < 1) requestAnimationFrame(tick);
          }
          requestAnimationFrame(tick);
          io.unobserve(el);
        });
      },
      { threshold: 0.5 }
    );
    counters.forEach(el => io.observe(el));
  }

  /* ── Stagger children ─────────────────────────────────────── */
  function initStagger() {
    document.querySelectorAll('[data-stagger]').forEach(parent => {
      const children = parent.children;
      const delay = parseInt(parent.dataset.stagger || '80');
      Array.from(children).forEach((child, i) => {
        child.style.transitionDelay = (i * delay) + 'ms';
        child.classList.add('reveal');
      });
    });
    initReveal();
  }

  /* ── Navbar scroll state ──────────────────────────────────── */
  function initNavScroll() {
    const nav = document.getElementById('voidNav');
    if (!nav) return;
    const handler = () => nav.classList.toggle('scrolled', window.scrollY > 24);
    window.addEventListener('scroll', handler, { passive: true });
    handler();
  }

  /* ── Init ─────────────────────────────────────────────────── */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      initReveal();
      initCounters();
      initStagger();
      initNavScroll();
    });
  } else {
    initReveal();
    initCounters();
    initStagger();
    initNavScroll();
  }
})();
