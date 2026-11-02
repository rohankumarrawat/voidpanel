import React from 'react';

export const Logo = ({ size = 40, style = {} }) => {
  return (
    <div
      className="ox-preloader-logo flex-shrink-0"
      style={{
        width: size,
        height: size,
        background: 'var(--ox-grad-brand, linear-gradient(135deg, #f59e0b 0%, #d97706 100%))',
        borderRadius: size > 45 ? 14 : 10,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        border: '1px solid rgba(255,255,255,0.12)',
        boxShadow: '0 4px 12px rgba(245, 158, 11, 0.25)',
        ...style,
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

export default Logo;
