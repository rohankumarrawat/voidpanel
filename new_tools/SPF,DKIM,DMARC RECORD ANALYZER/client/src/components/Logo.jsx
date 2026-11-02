import React from 'react';

export const Logo = () => {
  return (
    <div
      className="ox-preloader-logo"
      style={{
        width: 48,
        height: 48,
        background: 'linear-gradient(135deg, #f59e0b, #d97706)',
        borderRadius: 12,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        border: '1px solid rgba(255,255,255,0.2)',
        boxShadow: '0 4px 12px rgba(245, 158, 11, 0.25)',
        flexShrink: 0,
      }}
    >
      <img
        src="https://voidonyx.com/static/voidonyx/logo_emblem.png"
        alt="VoidOnyx"
        style={{ width: '80%', height: '80%', objectFit: 'contain' }}
      />
    </div>
  );
};
