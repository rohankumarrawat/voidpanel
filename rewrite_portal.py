import re

with open('website/voidpanel/templates/portal.html', 'r') as f:
    content = f.read()

# Add CSS for tabs
css_addition = """
        /* ─── Tab Panels ────────────────────────────────── */
        .p-tab-panel {
            display: none;
            animation: fadeIn 0.3s ease;
        }
        .p-tab-panel.active {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(5px); }
            to { opacity: 1; transform: translateY(0); }
        }
"""
content = content.replace("/* ─── Main Panel ──────────────────────────────────── */", css_addition + "\n        /* ─── Main Panel ──────────────────────────────────── */")

# The JavaScript to switch tabs
js_old = """function setActive(el) {
    document.querySelectorAll('.p-nav-item').forEach(a => a.classList.remove('active'));
    el.classList.add('active');
}
// Scroll-spy
const sections = ['overview','services','licenses','billing','support','activity'];
window.addEventListener('scroll', () => {
    const scrollY = window.scrollY + 120;
    let active = 'overview';
    sections.forEach(id => {
        const el = document.getElementById(id);
        if (el && el.offsetTop <= scrollY) active = id;
    });
    document.querySelectorAll('.p-nav-item').forEach(a => {
        const href = a.getAttribute('href');
        a.classList.toggle('active', href === '#' + active);
    });
});"""

js_new = """function setActive(el, tabId) {
    if (el) {
        document.querySelectorAll('.p-nav-item').forEach(a => a.classList.remove('active'));
        el.classList.add('active');
    }
    
    // Hide all panels
    document.querySelectorAll('.p-tab-panel').forEach(p => {
        p.classList.remove('active');
    });
    
    // Show selected panel
    const activePanel = document.getElementById('tab-' + tabId);
    if (activePanel) {
        activePanel.classList.add('active');
    }
}

// Check URL hash on load to open specific tab
document.addEventListener('DOMContentLoaded', () => {
    let hash = window.location.hash.substring(1);
    if (['overview','services','licenses','billing','support','activity'].includes(hash)) {
        const link = document.querySelector(`.p-nav-item[href="#${hash}"]`);
        setActive(link, hash);
    }
});"""
content = content.replace(js_old, js_new)

# Update sidebar links
content = content.replace('onclick="setActive(this)"', '')
content = content.replace('href="#overview" class="p-nav-item active"', 'href="#overview" class="p-nav-item active" onclick="setActive(this, \'overview\')"')
content = content.replace('href="#services" class="p-nav-item"', 'href="#services" class="p-nav-item" onclick="setActive(this, \'services\')"')
content = content.replace('href="#licenses" class="p-nav-item"', 'href="#licenses" class="p-nav-item" onclick="setActive(this, \'licenses\')"')
content = content.replace('href="#billing" class="p-nav-item"', 'href="#billing" class="p-nav-item" onclick="setActive(this, \'billing\')"')
content = content.replace('href="#support" class="p-nav-item"', 'href="#support" class="p-nav-item" onclick="setActive(this, \'support\')"')
content = content.replace('href="#activity" class="p-nav-item"', 'href="#activity" class="p-nav-item" onclick="setActive(this, \'activity\')"')

with open('website/voidpanel/templates/portal.html', 'w') as f:
    f.write(content)
