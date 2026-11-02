import React, { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

export default function CollapsibleSection({
  title,
  icon: Icon,
  badge,
  defaultOpen = true,
  children,
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="void-card rounded-xl border border-void-700/70 overflow-hidden transition-all">
      {/* Header Bar */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-5 py-4 bg-void-900/60 hover:bg-void-850 flex items-center justify-between transition-colors border-b border-void-700/50"
      >
        <div className="flex items-center gap-3">
          {Icon && <Icon className="w-4 h-4 text-cyan-glow" />}
          <span className="font-mono text-sm font-semibold uppercase tracking-wider text-slate-200">
            {title}
          </span>
          {badge !== undefined && badge !== null && (
            <span className="px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              {badge}
            </span>
          )}
        </div>

        <div className="text-slate-400">
          {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </div>
      </button>

      {/* Content Body */}
      {isOpen && <div className="p-5">{children}</div>}
    </div>
  );
}
