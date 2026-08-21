import { Link } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import { useState } from 'react'

export default function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <nav className="sticky top-0 z-50 bg-white/90 backdrop-blur-[20px] backdrop-saturate-[180%] border-b border-black/10" style={{ height: 72 }}>
      <div className="max-w-[1200px] mx-auto px-[5%] w-full h-full flex items-center justify-between gap-6">
        {/* Brand — matches VoidOnyx .ox-nav-brand */}
        <Link to="/" className="flex items-center gap-2.5 shrink-0 group">
          <div className="w-9 h-9 bg-ox-brand rounded-[10px] flex items-center justify-center shadow-ox-sm group-hover:shadow-ox-md transition-shadow">
            <i className="fa-solid fa-hexagon-nodes text-white text-base"></i>
          </div>
          <span className="text-[1.2rem] font-black tracking-[-0.03em] text-ox-navy">
            Void<span className="bg-ox-brand bg-clip-text text-transparent">Tools</span>
          </span>
        </Link>

        {/* Desktop Links — matches VoidOnyx .ox-nav-links */}
        <div className="hidden md:flex items-center gap-0.5">
          <Link to="/" className="text-[0.88rem] font-semibold text-ox-muted px-3.5 py-1.5 rounded-ox-sm hover:text-ox-navy hover:bg-ox-bg-alt transition-all">
            All Tools
          </Link>
          <Link to="/tools/dns-checker" className="text-[0.88rem] font-semibold text-ox-muted px-3.5 py-1.5 rounded-ox-sm hover:text-ox-navy hover:bg-ox-bg-alt transition-all">
            DNS Checker
          </Link>
          <a href="https://voidonyx.com" target="_blank" rel="noopener noreferrer" className="text-[0.88rem] font-semibold text-ox-muted px-3.5 py-1.5 rounded-ox-sm hover:text-ox-navy hover:bg-ox-bg-alt transition-all">
            VoidOnyx
          </a>
          <a href="https://voidpanel.com" target="_blank" rel="noopener noreferrer" className="text-[0.88rem] font-semibold text-ox-muted px-3.5 py-1.5 rounded-ox-sm hover:text-ox-navy hover:bg-ox-bg-alt transition-all">
            VoidPanel
          </a>
        </div>

        {/* Desktop CTA — matches VoidOnyx .ox-btn-primary */}
        <div className="hidden md:flex items-center gap-2.5 shrink-0">
          <a
            href="https://voidpanel.com/login/"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-1.5 px-[18px] py-2 rounded-ox-sm text-[0.84rem] font-bold border-[1.5px] border-black/[0.16] text-ox-navy/70 hover:bg-ox-bg-alt hover:border-ox-blue hover:text-ox-blue transition-all"
          >
            Sign In
          </a>
          <a
            href="https://voidpanel.com/register/"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-1.5 px-[18px] py-2 bg-ox-brand rounded-ox-sm text-[0.84rem] font-bold text-white shadow-ox-blue hover:translate-y-[-2px] hover:shadow-[0_8px_24px_rgba(37,99,235,0.40)] transition-all"
          >
            Get Started <i className="fa-solid fa-arrow-right text-[0.75rem]"></i>
          </a>
        </div>

        {/* Mobile Hamburger */}
        <button className="md:hidden p-1.5 rounded-ox-sm text-ox-navy/70" onClick={() => setMobileOpen(!mobileOpen)}>
          {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Mobile Menu */}
      {mobileOpen && (
        <div className="md:hidden bg-white border-t border-black/10 px-[5%] pb-5 space-y-1 shadow-ox-lg">
          <Link to="/" onClick={() => setMobileOpen(false)} className="block px-3 py-2.5 text-sm font-semibold text-ox-navy/80 rounded-ox-sm hover:bg-ox-bg-alt">
            All Tools
          </Link>
          <Link to="/tools/dns-checker" onClick={() => setMobileOpen(false)} className="block px-3 py-2.5 text-sm font-semibold text-ox-navy/80 rounded-ox-sm hover:bg-ox-bg-alt">
            DNS Checker
          </Link>
          <a href="https://voidonyx.com" target="_blank" rel="noopener noreferrer" className="block px-3 py-2.5 text-sm font-semibold text-ox-navy/80 rounded-ox-sm hover:bg-ox-bg-alt">
            VoidOnyx
          </a>
          <a href="https://voidpanel.com/register/" target="_blank" rel="noopener noreferrer" className="block px-3 py-2.5 text-sm font-bold text-ox-blue rounded-ox-sm hover:bg-blue-50">
            Get Started →
          </a>
        </div>
      )}
    </nav>
  )
}
