import React from 'react';
import { Layers, ShieldCheck, CornerDownRight, CheckCircle2 } from 'lucide-react';

export default function IssuerChain({ certChain = [], chainDepth = 1 }) {
  if (!certChain || certChain.length === 0) {
    return (
      <div className="p-4 rounded-lg bg-void-950 border border-void-700 text-xs font-mono text-slate-500">
        Certificate authority chain information is limited or single-tier.
      </div>
    );
  }

  return (
    <div className="space-y-3 font-mono text-xs">
      <div className="text-slate-400 text-xs flex items-center justify-between pb-2 border-b border-void-800">
        <span className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-cyan-glow" />
          <span>Chain Depth: <strong className="text-slate-200">{chainDepth} Tier(s)</strong></span>
        </span>
        <span className="text-slate-500">Leaf → Intermediate → Root</span>
      </div>

      <div className="space-y-2 pt-1">
        {certChain.map((node, index) => (
          <div
            key={index}
            style={{ marginLeft: `${index * 16}px` }}
            className={`p-3.5 rounded-lg border transition-all ${
              node.type === 'leaf'
                ? 'bg-cyan-500/10 border-cyan-500/30 text-slate-100'
                : node.type === 'root'
                ? 'bg-emerald-500/10 border-emerald-500/30 text-slate-100'
                : 'bg-void-950 border-void-700/80 text-slate-300'
            }`}
          >
            <div className="flex items-center justify-between gap-2 mb-1.5">
              <div className="flex items-center gap-2">
                {index > 0 && <CornerDownRight className="w-3.5 h-3.5 text-cyan-glow shrink-0" />}
                <span className="font-bold text-slate-100 truncate">
                  {node.subject?.cn || 'Unknown CN'}
                </span>
              </div>
              <span
                className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${
                  node.type === 'leaf'
                    ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                    : node.type === 'root'
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : 'bg-void-800 text-slate-400 border border-void-700'
                }`}
              >
                {node.type} Cert
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] text-slate-400 pt-1 border-t border-void-800/60">
              <div>
                <span className="text-slate-500 block">Organization:</span>
                <span className="text-slate-300">{node.subject?.o || 'N/A'}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Issued By:</span>
                <span className="text-slate-300">{node.issuer?.cn || 'N/A'}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
