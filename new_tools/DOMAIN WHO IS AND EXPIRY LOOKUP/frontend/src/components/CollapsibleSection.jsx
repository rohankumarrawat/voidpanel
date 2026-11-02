import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

export default function CollapsibleSection({ title, icon: Icon, defaultOpen = true, children, badge }) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border border-slate-200/90 rounded-2xl bg-white overflow-hidden shadow-sm">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-6 py-4.5 flex items-center justify-between bg-slate-50/60 hover:bg-slate-100/60 transition-colors text-left focus:outline-none"
      >
        <div className="flex items-center space-x-3">
          {Icon && (
            <div className="w-8 h-8 rounded-lg bg-white border border-slate-200 flex items-center justify-center text-rose-600 shadow-sm">
              <Icon className="w-4 h-4" />
            </div>
          )}
          <span className="text-sm font-bold text-slate-900 tracking-tight">{title}</span>
          {badge && (
            <span className="px-2.5 py-0.5 rounded-md text-[11px] font-mono bg-white border border-slate-200 text-slate-700 font-medium">
              {badge}
            </span>
          )}
        </div>

        <div className="text-slate-400 hover:text-slate-700">
          {isOpen ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </div>
      </button>

      {isOpen && <div className="p-6 border-t border-slate-100 bg-white">{children}</div>}
    </div>
  );
}
