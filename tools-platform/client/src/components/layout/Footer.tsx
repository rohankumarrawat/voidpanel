export default function Footer() {
  return (
    <footer className="border-t border-black/10 bg-white py-10 mt-16">
      <div className="max-w-[1200px] mx-auto px-[5%]">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          {/* Brand */}
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-ox-brand rounded-[8px] flex items-center justify-center">
              <i className="fa-solid fa-hexagon-nodes text-white text-sm"></i>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <span className="font-bold text-ox-navy">VoidOnyx Tools</span>
              <span className="text-ox-faint">•</span>
              <span className="text-ox-muted text-xs">Powered by VoidPanel</span>
            </div>
          </div>

          {/* Links */}
          <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-ox-muted">
            <a href="https://voidonyx.com" target="_blank" rel="noopener noreferrer" className="hover:text-ox-blue transition-colors">
              VoidOnyx
            </a>
            <a href="https://voidpanel.com" target="_blank" rel="noopener noreferrer" className="hover:text-ox-blue transition-colors">
              VoidPanel
            </a>
            <a href="https://voidonyx.com/docs/" target="_blank" rel="noopener noreferrer" className="hover:text-ox-blue transition-colors">
              Documentation
            </a>
            <a href="https://voidonyx.com/portal/ticket/new/" target="_blank" rel="noopener noreferrer" className="hover:text-ox-blue transition-colors">
              Support
            </a>
          </div>

          {/* Copyright */}
          <p className="text-xs text-ox-faint">
            © {new Date().getFullYear()} VoidOnyx. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  )
}
