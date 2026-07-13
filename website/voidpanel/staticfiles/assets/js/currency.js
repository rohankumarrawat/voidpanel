/**
 * VoidPanel Currency Engine v2.0
 * --------------------------------
 * - Base currency: INR (set by admin)
 * - Auto-detects user country → local currency via IP geolocation
 * - Fetches live exchange rates from open.er-api.com (free, no key)
 * - Caches rates in localStorage for 1 hour
 * - Converts all [data-price-inr] elements on the page
 * - Shows a currency selector badge bottom-right
 * - Exposes window.CurrencyEngine for JS integration
 */

(function () {
  'use strict';

  const CACHE_KEY = 'vp_currency_cache';
  const CACHE_TTL = 60 * 60 * 1000; // 1 hour

  // Supported currencies with metadata
  const CURRENCY_META = {
    INR: { symbol: '₹', name: 'Indian Rupee', flag: '🇮🇳', locale: 'en-IN' },
    USD: { symbol: '$', name: 'US Dollar', flag: '🇺🇸', locale: 'en-US' },
    EUR: { symbol: '€', name: 'Euro', flag: '🇪🇺', locale: 'de-DE' },
    GBP: { symbol: '£', name: 'British Pound', flag: '🇬🇧', locale: 'en-GB' },
    AED: { symbol: 'AED', name: 'UAE Dirham', flag: '🇦🇪', locale: 'ar-AE' },
    SGD: { symbol: 'S$', name: 'Singapore Dollar', flag: '🇸🇬', locale: 'en-SG' },
    AUD: { symbol: 'A$', name: 'Australian Dollar', flag: '🇦🇺', locale: 'en-AU' },
    CAD: { symbol: 'C$', name: 'Canadian Dollar', flag: '🇨🇦', locale: 'en-CA' },
    JPY: { symbol: '¥', name: 'Japanese Yen', flag: '🇯🇵', locale: 'ja-JP' },
    BDT: { symbol: '৳', name: 'Bangladeshi Taka', flag: '🇧🇩', locale: 'bn-BD' },
    PKR: { symbol: '₨', name: 'Pakistani Rupee', flag: '🇵🇰', locale: 'ur-PK' },
    MYR: { symbol: 'RM', name: 'Malaysian Ringgit', flag: '🇲🇾', locale: 'ms-MY' },
    NPR: { symbol: 'Rs', name: 'Nepali Rupee', flag: '🇳🇵', locale: 'ne-NP' },
    LKR: { symbol: 'Rs', name: 'Sri Lankan Rupee', flag: '🇱🇰', locale: 'si-LK' },
    NGN: { symbol: '₦', name: 'Nigerian Naira', flag: '🇳🇬', locale: 'en-NG' },
    ZAR: { symbol: 'R', name: 'South African Rand', flag: '🇿🇦', locale: 'en-ZA' },
  };

  const DEFAULT_CURRENCY = 'INR';

  // ── State ──────────────────────────────────────────────────────────────────
  let state = {
    currency: DEFAULT_CURRENCY,
    rate: 1,
    symbol: '₹',
    locale: 'en-IN',
    flag: '🇮🇳',
    name: 'Indian Rupee',
    ready: false,
  };

  // ── Public API ─────────────────────────────────────────────────────────────
  window.CurrencyEngine = {
    getState: () => ({ ...state }),
    convert: convertAmount,
    format: formatAmount,
    setCurrency: manualSetCurrency,
    refresh: init,
  };

  // ── Main entry ─────────────────────────────────────────────────────────────
  async function init() {
    try {
      const cached = loadCache();
      if (cached) {
        applyState(cached);
        renderAll();
        return;
      }

      // Detect user currency from IP
      const detectedCurrency = await detectCurrency();

      if (detectedCurrency === DEFAULT_CURRENCY) {
        // User is in India — no conversion needed
        applyState({
          currency: 'INR', rate: 1,
          symbol: '₹', locale: 'en-IN', flag: '🇮🇳', name: 'Indian Rupee',
        });
        saveCache(state);
        renderAll();
        return;
      }

      // Fetch live rate for detected currency
      const rate = await fetchRate(detectedCurrency);
      const meta = CURRENCY_META[detectedCurrency] || {
        symbol: detectedCurrency, name: detectedCurrency,
        flag: '🌍', locale: 'en-US',
      };

      applyState({
        currency: detectedCurrency,
        rate,
        symbol: meta.symbol,
        locale: meta.locale,
        flag: meta.flag,
        name: meta.name,
      });
      saveCache(state);
      renderAll();
    } catch (err) {
      console.warn('[VoidPanel Currency] Init error, using INR:', err);
      applyState({
        currency: 'INR', rate: 1,
        symbol: '₹', locale: 'en-IN', flag: '🇮🇳', name: 'Indian Rupee',
      });
      renderAll();
    }
  }

  // ── Geo detection ──────────────────────────────────────────────────────────
  async function detectCurrency() {
    // Check if manually overridden
    const manual = localStorage.getItem('vp_currency_manual');
    if (manual) return manual;

    try {
      const r = await fetch('https://ipapi.co/json/', { signal: AbortSignal.timeout(4000) });
      const d = await r.json();
      return d.currency || DEFAULT_CURRENCY;
    } catch {
      // Fallback: try another service
      try {
        const r2 = await fetch('https://api.country.is/', { signal: AbortSignal.timeout(3000) });
        const d2 = await r2.json();
        // Map country codes to currencies
        const COUNTRY_CURRENCY = {
          US: 'USD', GB: 'GBP', DE: 'EUR', FR: 'EUR', AE: 'AED',
          SG: 'SGD', AU: 'AUD', CA: 'CAD', JP: 'JPY', BD: 'BDT',
          PK: 'PKR', MY: 'MYR', NP: 'NPR', LK: 'LKR', NG: 'NGN',
          ZA: 'ZAR', IN: 'INR',
        };
        return COUNTRY_CURRENCY[d2.country] || DEFAULT_CURRENCY;
      } catch {
        return DEFAULT_CURRENCY;
      }
    }
  }

  // ── Rate fetching ──────────────────────────────────────────────────────────
  async function fetchRate(targetCurrency) {
    if (targetCurrency === DEFAULT_CURRENCY) return 1;
    const r = await fetch(
      `https://open.er-api.com/v6/latest/INR`,
      { signal: AbortSignal.timeout(5000) }
    );
    if (!r.ok) throw new Error('Rate fetch failed');
    const d = await r.json();
    const rate = d.rates[targetCurrency];
    if (!rate) throw new Error(`Rate not found for ${targetCurrency}`);
    return rate;
  }

  // ── Cache ──────────────────────────────────────────────────────────────────
  function saveCache(data) {
    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify({ ...data, ts: Date.now() }));
    } catch {}
  }

  function loadCache() {
    try {
      const raw = localStorage.getItem(CACHE_KEY);
      if (!raw) return null;
      const d = JSON.parse(raw);
      if (Date.now() - d.ts > CACHE_TTL) return null;

      // Respect manual override — invalidate cache if it doesn't match
      const manual = localStorage.getItem('vp_currency_manual');
      if (manual && manual !== d.currency) return null;

      return d;
    } catch {
      return null;
    }
  }

  // ── Conversion ─────────────────────────────────────────────────────────────
  function convertAmount(inrAmount) {
    const num = parseFloat(inrAmount);
    if (isNaN(num)) return inrAmount;
    return num * state.rate;
  }

  function formatAmount(inrAmount) {
    const converted = convertAmount(inrAmount);
    try {
      return new Intl.NumberFormat(state.locale, {
        style: 'currency',
        currency: state.currency,
        maximumFractionDigits: state.currency === 'JPY' ? 0 : 2,
        minimumFractionDigits: state.currency === 'JPY' ? 0 : 2,
      }).format(converted);
    } catch {
      return state.symbol + ' ' + converted.toFixed(2);
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  function renderAll() {
    state.ready = true;

    // Convert all tagged elements
    document.querySelectorAll('[data-price-inr]').forEach(el => {
      const inr = parseFloat(el.getAttribute('data-price-inr'));
      if (!isNaN(inr)) {
        el.textContent = formatAmount(inr);
        el.setAttribute('title', `₹${inr.toLocaleString('en-IN')} INR`);
        el.classList.add('price-converted');
      }
    });

    // Also handle elements that have data-price-inr-append="/mo" suffix
    document.querySelectorAll('[data-price-inr-suffix]').forEach(el => {
      const inr = parseFloat(el.getAttribute('data-price-inr'));
      const suffix = el.getAttribute('data-price-inr-suffix') || '';
      if (!isNaN(inr)) {
        el.innerHTML = `${formatAmount(inr)}<span class="price-suffix">${suffix}</span>`;
        el.setAttribute('title', `₹${inr.toLocaleString('en-IN')} INR`);
      }
    });

    // Fire event for custom JS to hook into
    window.dispatchEvent(new CustomEvent('vp:currency:ready', { detail: state }));

    // Render badge
    renderBadge();
  }

  function applyState(data) {
    Object.assign(state, data);
  }

  // ── Currency Selector Badge ────────────────────────────────────────────────
  function renderBadge() {
    let badge = document.getElementById('vp-currency-badge');
    if (!badge) {
      badge = document.createElement('div');
      badge.id = 'vp-currency-badge';
      badge.innerHTML = `
        <style>
          #vp-currency-badge {
            position: fixed; bottom: 20px; left: 20px; z-index: 9999;
            font-family: 'Inter', system-ui, sans-serif;
          }
          #vp-cb-btn {
            display: flex; align-items: center; gap: 7px;
            padding: 8px 14px; border-radius: 999px;
            background: rgba(7,16,26,0.92); border: 1px solid rgba(89,196,188,0.35);
            color: #e2f0ff; font-size: 0.78rem; font-weight: 700;
            cursor: pointer; backdrop-filter: blur(12px);
            box-shadow: 0 4px 24px rgba(0,0,0,0.4);
            transition: all 0.2s ease;
            user-select: none;
          }
          #vp-cb-btn:hover { border-color: #59c4bc; background: rgba(7,16,26,0.98); }
          #vp-cb-dot {
            width: 7px; height: 7px; border-radius: 50%;
            background: #59c4bc; flex-shrink:0;
          }
          #vp-cb-popup {
            display: none; position: absolute; bottom: 44px; left: 0;
            background: #0c1825; border: 1px solid rgba(89,196,188,0.2);
            border-radius: 16px; padding: 12px;
            min-width: 240px; max-height: 320px; overflow-y: auto;
            box-shadow: 0 16px 48px rgba(0,0,0,0.6);
            scrollbar-width: thin;
          }
          #vp-cb-popup.open { display: block; animation: vp-popup-in 0.18s ease; }
          @keyframes vp-popup-in {
            from { opacity:0; transform: translateY(8px); }
            to { opacity:1; transform: translateY(0); }
          }
          .vp-cb-item {
            display: flex; align-items: center; gap: 10px;
            padding: 9px 12px; border-radius: 10px; cursor: pointer;
            font-size: 0.83rem; color: #a0b0c4; transition: all 0.15s;
          }
          .vp-cb-item:hover { background: rgba(89,196,188,0.08); color: #e2f0ff; }
          .vp-cb-item.active { background: rgba(89,196,188,0.12); color: #59c4bc; font-weight: 700; }
          .vp-cb-sep { font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
            letter-spacing: 0.1em; color: #3a4f65; padding: 4px 12px 6px; }
        </style>
        <div id="vp-cb-popup"></div>
        <div id="vp-cb-btn">
          <div id="vp-cb-dot"></div>
          <span id="vp-cb-label"></span>
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
            <path d="M2 4L5 7L8 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </div>
      `;
      document.body.appendChild(badge);

      document.getElementById('vp-cb-btn').addEventListener('click', () => {
        const popup = document.getElementById('vp-cb-popup');
        popup.classList.toggle('open');
        if (popup.classList.contains('open')) buildPopup(popup);
      });

      // Close on outside click
      document.addEventListener('click', (e) => {
        if (!badge.contains(e.target)) {
          document.getElementById('vp-cb-popup').classList.remove('open');
        }
      });
    }

    // Update label
    const label = document.getElementById('vp-cb-label');
    if (label) label.textContent = `${state.flag} ${state.currency}`;
  }

  function buildPopup(popup) {
    const currencies = Object.entries(CURRENCY_META);
    let html = '<div class="vp-cb-sep">Select Currency</div>';
    currencies.forEach(([code, meta]) => {
      const active = code === state.currency ? 'active' : '';
      html += `<div class="vp-cb-item ${active}" onclick="window.CurrencyEngine.setCurrency('${code}')">
        <span>${meta.flag}</span>
        <span><strong>${code}</strong> — ${meta.name}</span>
      </div>`;
    });
    popup.innerHTML = html;
  }

  // ── Manual override ────────────────────────────────────────────────────────
  async function manualSetCurrency(code) {
    // Close popup
    const popup = document.getElementById('vp-cb-popup');
    if (popup) popup.classList.remove('open');

    localStorage.setItem('vp_currency_manual', code);
    // Invalidate cache so it refetches rate
    localStorage.removeItem(CACHE_KEY);

    // Re-initialize
    await init();
  }

  // ── Boot ───────────────────────────────────────────────────────────────────
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
