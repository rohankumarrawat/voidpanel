import React, { useState } from 'react';
import { History, Globe, User, ArrowUpRight, Clock, Trash2 } from 'lucide-react';

export default function RecentSearches({ myHistory = [], globalHistory = [], onSelectDomain, onClearMyHistory }) {
  const [activeTab, setActiveTab] = useState('split'); // 'split' | 'my' | 'global'

  const renderHistoryGrid = (items, emptyMessage) => {
    if (!items || items.length === 0) {
      return (
        <div className="p-6 rounded-xl bg-slate-50 border border-slate-200/80 text-center space-y-2">
          <Clock className="w-6 h-6 text-slate-400 mx-auto" />
          <p className="text-xs font-mono text-slate-500">{emptyMessage}</p>
        </div>
      );
    }

    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {items.map((item, idx) => {
          let statusColor = 'text-emerald-700 border-emerald-200 bg-emerald-50';
          if (item.status === 'expired') statusColor = 'text-red-700 border-red-200 bg-red-50';
          else if (item.status === 'expiring') statusColor = 'text-amber-700 border-amber-200 bg-amber-50';
          else if (item.status === 'available') statusColor = 'text-blue-700 border-blue-200 bg-blue-50';

          return (
            <button
              key={idx}
              type="button"
              onClick={() => onSelectDomain(item.domain)}
              className="p-3.5 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200/80 hover:border-slate-300 text-left transition-all group flex items-center justify-between shadow-sm"
            >
              <div className="space-y-1 overflow-hidden">
                <span className="font-mono text-sm font-bold text-slate-900 group-hover:text-rose-600 truncate block">
                  {item.domain}
                </span>

                <div className="flex items-center space-x-2 text-[11px] font-mono">
                  <span className={`px-2 py-0.5 rounded-md border font-semibold ${statusColor}`}>
                    {item.status}
                  </span>
                  {item.daysRemaining !== null && item.daysRemaining !== undefined && (
                    <span className="text-slate-500">{item.daysRemaining}d left</span>
                  )}
                </div>
              </div>

              <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-rose-600 transition-colors flex-shrink-0" />
            </button>
          );
        })}
      </div>
    );
  };

  return (
    <div className="w-full max-w-4xl mx-auto pt-6 space-y-4">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-3">
        <div className="flex items-center space-x-2">
          <History className="w-5 h-5 text-slate-800" />
          <h3 className="text-base font-bold text-slate-900">Lookup History & Live Feed</h3>
        </div>

        {/* Tab filters */}
        <div className="flex items-center space-x-1 p-1 rounded-xl bg-white border border-slate-200 text-xs font-mono shadow-sm">
          <button
            type="button"
            onClick={() => setActiveTab('split')}
            className={`px-3 py-1.5 rounded-lg transition-all font-semibold ${
              activeTab === 'split' ? 'bg-slate-900 text-white' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            2-Column View
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('my')}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1 font-semibold ${
              activeTab === 'my' ? 'bg-slate-900 text-white' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <User className="w-3.5 h-3.5" /> My History
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('global')}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1 font-semibold ${
              activeTab === 'global' ? 'bg-slate-900 text-white' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Globe className="w-3.5 h-3.5" /> Global Feed
          </button>
        </div>
      </div>

      {/* Dual Column Layout */}
      {activeTab === 'split' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* My History Column */}
          <div className="border border-slate-200/90 rounded-[24px] bg-white p-6 shadow-card space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2 text-xs font-mono text-rose-600 uppercase tracking-wider font-bold">
                <User className="w-4 h-4 text-rose-600" />
                <span>My Browser History</span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="px-2.5 py-0.5 rounded-md text-[10px] font-mono bg-slate-100 border border-slate-200 text-slate-700 font-semibold">
                  This Browser Session
                </span>
                {myHistory.length > 0 && onClearMyHistory && (
                  <button
                    type="button"
                    onClick={onClearMyHistory}
                    className="p-1 rounded text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                    title="Clear My History"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>

            {renderHistoryGrid(myHistory, 'No domain searches in this browser session yet. Enter a domain above!')}
          </div>

          {/* Global Lookups Feed Column */}
          <div className="border border-slate-200/90 rounded-[24px] bg-white p-6 shadow-card space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2 text-xs font-mono text-emerald-700 uppercase tracking-wider font-bold">
                <Globe className="w-4 h-4 text-emerald-600" />
                <span>Global Community Feed</span>
              </div>
              <span className="px-2.5 py-0.5 rounded-md text-[10px] font-mono bg-emerald-50 border border-emerald-200 text-emerald-800 font-semibold flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> System Feed
              </span>
            </div>

            {renderHistoryGrid(globalHistory, 'No global lookups recorded yet.')}
          </div>
        </div>
      )}

      {/* Single Tab: My History */}
      {activeTab === 'my' && (
        <div className="border border-slate-200/90 rounded-[24px] bg-white p-6 shadow-card space-y-4">
          <div className="flex items-center space-x-2 text-xs font-mono text-rose-600 uppercase tracking-wider font-bold">
            <User className="w-4 h-4 text-rose-600" />
            <span>My Browser Session History</span>
          </div>
          {renderHistoryGrid(myHistory, 'No domain searches in this browser session yet.')}
        </div>
      )}

      {/* Single Tab: Global Feed */}
      {activeTab === 'global' && (
        <div className="border border-slate-200/90 rounded-[24px] bg-white p-6 shadow-card space-y-4">
          <div className="flex items-center space-x-2 text-xs font-mono text-emerald-700 uppercase tracking-wider font-bold">
            <Globe className="w-4 h-4 text-emerald-600" />
            <span>Global System Lookups Feed</span>
          </div>
          {renderHistoryGrid(globalHistory, 'No global lookups recorded yet.')}
        </div>
      )}
    </div>
  );
}
