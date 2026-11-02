import React from 'react';
import VoidPanelLogo from './VoidPanelLogo';
import { GitCompare, Terminal, History, ArrowLeft } from 'lucide-react';

export default function Navbar({ onOpenDiff, onOpenCurl, onOpenHistory, traceData }) {
  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-slate-200/80 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
        {/* Left: Brand Logo & Subtitle */}
        <a href="#" className="flex items-center">
          <VoidPanelLogo showSubtitle={true} />
        </a>

        {/* Right: Tools & Controls */}
        <div className="flex items-center space-x-4 text-xs font-semibold">
          {traceData && (
            <>
              <button
                type="button"
                onClick={onOpenDiff}
                className="px-3 py-2 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 hover:text-[#FF5C00] flex items-center space-x-1.5 transition-all shadow-xs"
                title="Compare Header Hops"
              >
                <GitCompare className="w-3.5 h-3.5 text-purple-600" />
                <span className="hidden sm:inline">Diff Hops</span>
              </button>

              <button
                type="button"
                onClick={() => onOpenCurl(null)}
                className="px-3 py-2 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 hover:text-[#FF5C00] flex items-center space-x-1.5 transition-all shadow-xs"
                title="Generate cURL / CLI Script"
              >
                <Terminal className="w-3.5 h-3.5 text-blue-600" />
                <span className="hidden sm:inline">cURL Script</span>
              </button>
            </>
          )}

          <button
            type="button"
            onClick={onOpenHistory}
            className="p-2 sm:px-3 sm:py-2 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 hover:text-[#FF5C00] flex items-center space-x-1.5 transition-all shadow-xs"
            title="History"
          >
            <History className="w-3.5 h-3.5 text-[#FF5C00]" />
            <span className="hidden sm:inline">History</span>
          </button>

          {/* All Tools link matching tools.voidonyx.in */}
          <a
            href="https://tools.voidonyx.in"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center space-x-1.5 px-3 py-2 rounded-xl text-slate-700 hover:text-[#FF5C00] hover:bg-slate-50 font-bold transition-all"
          >
            <ArrowLeft className="w-4 h-4 text-slate-500" />
            <span>All Tools</span>
          </a>
        </div>
      </div>
    </header>
  );
}
