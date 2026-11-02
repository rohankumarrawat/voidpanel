import React from 'react';
import { ArrowLeft } from 'lucide-react';

export default function Header() {
  return (
    <header className="border-b border-slate-200/80 bg-white sticky top-0 z-50 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
        {/* Brand Logo & Title */}
        <div className="flex items-center space-x-3.5">
          <div
            className="ox-preloader-logo flex-shrink-0"
            style={{
              width: 50,
              height: 50,
              background: 'var(--ox-grad-brand, linear-gradient(135deg, #f59e0b 0%, #d97706 100%))',
              borderRadius: 12,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1px solid rgba(255,255,255,0.2)',
              boxShadow: '0 4px 12px rgba(245, 158, 11, 0.25)'
            }}
          >
            <img
              src="https://voidonyx.com/static/voidonyx/logo_emblem.png"
              alt="VoidOnyx"
              style={{ width: '80%', height: '80%', objectFit: 'contain' }}
            />
          </div>

          <div>
            <h1 className="text-base sm:text-lg font-bold text-slate-900 leading-tight">
              VoidOnyx Tools
            </h1>
            <p className="text-xs text-slate-500 font-medium">
              Domain WHOIS & Expiry Checker
            </p>
          </div>
        </div>

        {/* Back link */}
        <div>
          <a
            href="https://tools.voidonyx.in"
            className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>All Tools</span>
          </a>
        </div>
      </div>
    </header>
  );
}
