import React from 'react';

export default function VoidPanelLogo({ showSubtitle = true }) {
  return (
    <div className="flex items-center space-x-3.5 select-none">
      {/* VoidPanel Official Emblem Box */}
      <div
        className="shrink-0 flex items-center justify-center shadow-md shadow-orange-500/20"
        style={{
          width: 46,
          height: 46,
          background: 'linear-gradient(135deg, #FF7A00 0%, #E04D00 100%)',
          borderRadius: 13,
          border: '1px solid rgba(255,255,255,0.25)',
        }}
      >
        <img
          src="/favicon.png"
          alt="VoidPanel"
          style={{ width: '75%', height: '75%', objectFit: 'contain' }}
        />
      </div>

      {/* VoidPanel Tools Title & Subtitle */}
      <div className="flex flex-col">
        <span className="text-base font-extrabold tracking-tight text-slate-900 leading-tight">
          VoidPanel Tools
        </span>
        {showSubtitle && (
          <span className="text-xs font-semibold text-slate-500">
            HTTP Header & Redirect Tracer
          </span>
        )}
      </div>
    </div>
  );
}
