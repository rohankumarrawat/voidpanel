import React from 'react';
import { ArrowLeft } from 'lucide-react';
import Logo from './Logo';

export default function Header() {
  return (
    <header className="bg-white border-b border-slate-200/80 sticky top-0 z-40 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        
        {/* Brand & Logo matching tools.voidonyx.in */}
        <div className="flex items-center gap-3">
          <Logo size={42} />
          <div>
            <h1 className="text-base font-bold text-slate-900 leading-tight">
              VoidOnyx Tools
            </h1>
            <p className="text-xs font-medium text-slate-500">
              SSL/TLS Certificate Expiry Checker
            </p>
          </div>
        </div>

        {/* All Tools Navigation */}
        <div className="flex items-center gap-4">
          <a 
            href="https://tools.voidonyx.in" 
            className="flex items-center gap-1.5 text-sm font-semibold text-slate-600 hover:text-slate-900 transition-colors px-3 py-1.5 rounded-lg hover:bg-slate-100"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>All Tools</span>
          </a>
        </div>
      </div>
    </header>
  );
}


