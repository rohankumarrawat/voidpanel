import React from 'react';
import { Logo } from './Logo';

export default function Header() {
  return (
    <header className="top-navbar">
      <div className="navbar-container">
        <div className="brand-group">
          <Logo />
          <div className="brand-text">
            <h2 className="brand-title">VoidOnyx Tools</h2>
            <p className="brand-subtitle">SPF, DKIM & DMARC Record Analyzer</p>
          </div>
        </div>

        <a href="https://tools.voidonyx.in" className="back-link" target="_blank" rel="noopener noreferrer">
          <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          <span>All Tools</span>
        </a>
      </div>
    </header>
  );
}
