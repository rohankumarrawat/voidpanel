import React from 'react';
import { Shield, Lock } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white mt-16 py-12 text-xs font-sans text-slate-500">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div
              className="ox-preloader-logo flex-shrink-0"
              style={{
                width: 38,
                height: 38,
                background: 'var(--ox-grad-brand, linear-gradient(135deg, #f59e0b 0%, #d97706 100%))',
                borderRadius: 10,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: '1px solid rgba(255,255,255,0.2)',
                boxShadow: '0 3px 8px rgba(245, 158, 11, 0.2)'
              }}
            >
              <img
                src="https://voidonyx.com/static/voidonyx/logo_emblem.png"
                alt="VoidOnyx"
                style={{ width: '80%', height: '80%', objectFit: 'contain' }}
              />
            </div>
            <div>
              <span className="text-slate-900 font-bold block text-sm">VoidOnyx Tools</span>
              <span className="text-slate-500 font-medium">Domain WHOIS, RDAP & Expiration Intelligence</span>
            </div>
          </div>

          <div className="flex items-center space-x-6 text-slate-600 font-medium">
            <span className="flex items-center gap-1.5">
              <Shield className="w-4 h-4 text-rose-600" /> TCP Port 43 + RDAP RFC 7482
            </span>
            <span className="flex items-center gap-1.5">
              <Lock className="w-4 h-4 text-emerald-600" /> Zero Logging Privacy
            </span>
          </div>
        </div>

        <div className="border-t border-slate-100 pt-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-slate-500 font-medium">
          <p>© {new Date().getFullYear()} VoidOnyx Security (tools.voidonyx.in). All rights reserved.</p>
          <p className="text-slate-400">Built for network engineers, sysadmins, and security analysts.</p>
        </div>
      </div>
    </footer>
  );
}
