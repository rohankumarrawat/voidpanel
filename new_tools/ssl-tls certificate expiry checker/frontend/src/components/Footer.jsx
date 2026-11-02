import React from 'react';
import { ArrowUpRight } from 'lucide-react';
import Logo from './Logo';

export default function Footer() {
  return (
    <footer className="border-t border-slate-200/80 bg-white mt-16 py-10 text-xs text-slate-500 font-sans">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-100 pb-6">
          <div className="flex items-center gap-3">
            <Logo size={34} />
            <div>
              <span className="font-bold text-slate-900 text-sm">VoidOnyx Tools</span>
              <p className="text-slate-500 text-xs">
                Stateless, high-performance web utility tools.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-4 text-xs font-medium">
            <a href="https://tools.voidonyx.in" className="text-slate-600 hover:text-slate-900 transition-colors flex items-center gap-1">
              <span>All Tools</span>
              <ArrowUpRight className="w-3 h-3" />
            </a>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-[11px] text-slate-400">
          <div>
            &copy; {new Date().getFullYear()} VoidOnyx Security Labs. All rights reserved.
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            <span className="text-slate-600 font-medium">All Systems Operational</span>
          </div>
        </div>
      </div>
    </footer>
  );
}


