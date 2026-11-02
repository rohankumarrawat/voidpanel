import React, { useEffect, useState } from 'react';
import { History, X, Trash2, ArrowRight, Clock, Database, Globe, User, RefreshCw } from 'lucide-react';

export default function TraceHistoryDrawer({ isOpen, onClose, history: localHistory, onSelectHistory, onClearHistory }) {
  const [activeTab, setActiveTab] = useState('global'); // 'global' or 'personal'
  const [globalHistory, setGlobalHistory] = useState([]);
  const [loadingGlobal, setLoadingGlobal] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchGlobalHistory();
    }
  }, [isOpen]);

  const fetchGlobalHistory = async () => {
    setLoadingGlobal(true);
    try {
      const res = await fetch('/api/history?limit=30&type=global');
      const data = await res.json();
      if (data.success && Array.isArray(data.data)) {
        const formatted = data.data.map(item => ({
          id: item.id,
          url: item.input_url,
          finalUrl: item.final_url,
          hops: item.total_hops,
          timeMs: item.total_time_ms,
          score: item.security_score,
          grade: item.security_grade,
          finalStatus: `${item.final_status_code || 200} ${item.final_status_text || 'OK'}`,
          timestamp: new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          date: new Date(item.created_at).toLocaleDateString([], { month: 'short', day: 'numeric' })
        }));
        setGlobalHistory(formatted);
      }
    } catch (e) {
      console.warn('MongoDB global history fetch failed:', e);
    } finally {
      setLoadingGlobal(false);
    }
  };

  const handleClearGlobalDB = async () => {
    if (window.confirm('Are you sure you want to clear the shared Global MongoDB history? This will delete all logged scans.')) {
      try {
        await fetch('/api/history', { method: 'DELETE' });
        setGlobalHistory([]);
      } catch (e) {
        console.error('Failed to clear Global DB history:', e);
      }
    }
  };

  if (!isOpen) return null;

  const currentDisplayList = activeTab === 'global' ? globalHistory : (localHistory || []);

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
      <div className="bg-white w-full max-w-lg h-full p-6 border-l border-slate-200 shadow-2xl flex flex-col relative">
        {/* Top Header */}
        <div className="flex items-center justify-between border-b border-slate-200 pb-4 shrink-0">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-orange-50 text-[#FF5C00] border border-orange-200 shadow-xs">
              <History className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-lg font-extrabold text-slate-900">Scan History</h3>
                <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-extrabold flex items-center space-x-1">
                  <Database className="w-3 h-3 text-emerald-600" />
                  <span>MongoDB Live</span>
                </span>
              </div>
              <p className="text-xs text-slate-500 font-medium">Uniform live scan history across all users</p>
            </div>
          </div>

          <div className="flex items-center space-x-1">
            <button
              type="button"
              onClick={fetchGlobalHistory}
              className="p-2 rounded-xl text-slate-400 hover:text-slate-900 hover:bg-slate-100 transition-colors"
              title="Refresh Global History"
            >
              <RefreshCw className={`w-4 h-4 ${loadingGlobal ? 'animate-spin text-[#FF5C00]' : ''}`} />
            </button>
            <button
              type="button"
              onClick={onClose}
              className="p-2 rounded-xl text-slate-400 hover:text-slate-900 hover:bg-slate-100 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tab Selector: Global History vs My History */}
        <div className="my-4 p-1 bg-slate-100/90 rounded-2xl flex items-center shrink-0 border border-slate-200">
          <button
            type="button"
            onClick={() => setActiveTab('global')}
            className={`flex-1 py-2 px-3 rounded-xl text-xs font-extrabold flex items-center justify-center space-x-2 transition-all ${
              activeTab === 'global'
                ? 'bg-white text-slate-900 shadow-sm border border-slate-200/80'
                : 'text-slate-500 hover:text-slate-900'
            }`}
          >
            <Globe className={`w-4 h-4 ${activeTab === 'global' ? 'text-[#FF5C00]' : 'text-slate-400'}`} />
            <span>Global History</span>
            <span className="ml-1 px-1.5 py-0.2 rounded-full bg-orange-100 text-[#FF5C00] text-[10px]">
              {globalHistory.length}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('personal')}
            className={`flex-1 py-2 px-3 rounded-xl text-xs font-extrabold flex items-center justify-center space-x-2 transition-all ${
              activeTab === 'personal'
                ? 'bg-white text-slate-900 shadow-sm border border-slate-200/80'
                : 'text-slate-500 hover:text-slate-900'
            }`}
          >
            <User className={`w-4 h-4 ${activeTab === 'personal' ? 'text-purple-600' : 'text-slate-400'}`} />
            <span>My History</span>
            <span className="ml-1 px-1.5 py-0.2 rounded-full bg-slate-200 text-slate-700 text-[10px]">
              {localHistory ? localHistory.length : 0}
            </span>
          </button>
        </div>

        {/* History Item Cards List */}
        <div className="flex-1 overflow-y-auto space-y-3 scrollbar-thin pr-1">
          {loadingGlobal && currentDisplayList.length === 0 ? (
            <div className="text-center py-16 text-slate-500 space-y-2">
              <RefreshCw className="w-8 h-8 mx-auto text-[#FF5C00] animate-spin opacity-80" />
              <p className="text-sm font-semibold text-slate-700">Loading live scans from MongoDB...</p>
            </div>
          ) : currentDisplayList.length === 0 ? (
            <div className="text-center py-16 text-slate-500 space-y-2">
              <History className="w-8 h-8 mx-auto text-slate-400 opacity-60" />
              <p className="text-sm font-semibold text-slate-700">No trace scans recorded.</p>
              <p className="text-xs max-w-xs mx-auto text-slate-500 font-medium">
                {activeTab === 'global'
                  ? 'Trace any domain or IPv4 target above to log it to MongoDB.'
                  : 'Your personal session history is empty.'}
              </p>
            </div>
          ) : (
            currentDisplayList.map((item, idx) => (
              <div
                key={item.id || idx}
                onClick={() => {
                  onSelectHistory(item);
                  onClose();
                }}
                className="group cursor-pointer rounded-2xl p-4 bg-slate-50 hover:bg-white border border-slate-200 hover:border-[#FF5C00] transition-all flex items-center justify-between gap-3 shadow-sm hover:shadow-md"
              >
                <div className="space-y-1.5 min-w-0 flex-1">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-mono font-extrabold text-slate-900 truncate group-hover:text-[#FF5C00] transition-colors max-w-[240px]">
                      {item.url}
                    </p>

                    {item.grade && (
                      <span className={`px-2 py-0.5 rounded-md text-[10px] font-black ${
                        item.grade.startsWith('A') ? 'bg-emerald-100 text-emerald-800' :
                        item.grade === 'B' ? 'bg-blue-100 text-blue-800' :
                        item.grade === 'C' ? 'bg-amber-100 text-amber-800' : 'bg-rose-100 text-rose-800'
                      }`}>
                        {item.grade} Grade ({item.score || 0})
                      </span>
                    )}
                  </div>

                  <div className="flex items-center space-x-2 text-[10px] font-semibold text-slate-600">
                    <span className="px-2 py-0.5 rounded-md bg-slate-200 text-slate-800 font-mono">
                      {item.hops} {item.hops === 1 ? 'hop' : 'hops'}
                    </span>

                    {item.timeMs && (
                      <span className="px-2 py-0.5 rounded-md bg-orange-50 text-[#FF5C00] font-mono border border-orange-100">
                        {item.timeMs} ms
                      </span>
                    )}

                    <span className="px-2 py-0.5 rounded-md bg-emerald-100 text-emerald-800 font-mono font-bold">
                      {item.finalStatus}
                    </span>

                    <span className="text-slate-400 flex items-center space-x-1 font-mono text-[9px] ml-auto">
                      <Clock className="w-3 h-3 text-slate-400" />
                      <span>{item.date || ''} {item.timestamp}</span>
                    </span>
                  </div>
                </div>

                <div className="p-2 rounded-xl bg-white text-slate-400 group-hover:text-white group-hover:bg-[#FF5C00] border border-slate-200 transition-all shrink-0 shadow-sm">
                  <ArrowRight className="w-4 h-4" />
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="mt-4 pt-4 border-t border-slate-200 flex justify-between items-center shrink-0">
          {activeTab === 'personal' && localHistory && localHistory.length > 0 && (
            <button
              type="button"
              onClick={onClearHistory}
              className="px-3.5 py-2 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded-xl text-xs font-bold flex items-center space-x-1.5 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Clear My History</span>
            </button>
          )}

          {activeTab === 'global' && globalHistory.length > 0 && (
            <button
              type="button"
              onClick={handleClearGlobalDB}
              className="px-3.5 py-2 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded-xl text-xs font-bold flex items-center space-x-1.5 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Clear Global DB</span>
            </button>
          )}

          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-200 rounded-xl text-xs font-semibold transition-colors ml-auto"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
