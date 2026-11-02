"""
VoidPanel AI Site Generator Engine
----------------------------------
Generates complete, production-ready, responsive single-file websites using Google Gemini,
handles iterative conversational editing, and publishes directly to production public_html.
"""

import os
import re
import shutil
import logging
from django.utils import timezone
from django.conf import settings
from .gemini_pool import GeminiPoolManager
from .models import AISiteProject, AISiteRevision, SiteLeadCapture

logger = logging.getLogger(__name__)


SITE_BUILDER_SYSTEM_PROMPT = """You are VoidPanel AI Site Architect — a world-class principal frontend engineer and elite UI/UX designer known for creating award-winning, Stripe/Linear/Vercel-grade landing pages and web apps.
Your mission is to generate complete, single-file, production-grade, aesthetically stunning responsive HTML5 websites.

STRICT TECHNICAL AND AESTHETIC STANDARDS:
1. COMPLETE STANDALONE HTML5:
   - Output must be a 100% self-contained valid HTML5 document starting with <!DOCTYPE html> and closing with </html>.
   - No external local dependencies. All stylesheets, fonts, and scripts must load from high-speed reliable CDNs.

2. MODERN DESIGN SYSTEM & AESTHETICS (STRIPE / LINEAR GRADE):
   - Load Tailwind CSS CDN in <head>: <script src="https://cdn.tailwindcss.com"></script>
   - Load Font Awesome 6 Icons in <head>: <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
   - Load Google Fonts (Plus Jakarta Sans or Inter):
     <link rel="preconnect" href="https://fonts.googleapis.com">
     <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
     <style>body { font-family: 'Plus Jakarta Sans', sans-serif; }</style>
   - Curated Color Palettes (NEVER use harsh, cheap pure yellow or garish saturated tones):
     * Tech / SaaS / Hosting / Agency: Ultra-deep dark mode (slate-950 / #080b14 base), indigo-500/cyan-400 or violet-500 gradients, subtle glowing borders (border-white/10), glass cards (bg-slate-900/60 backdrop-blur-xl).
     * Modern Business / Corporate: Clean dark navy or crisp white with royal blue / emerald green trust badges, subtle shadows.
     * Luxury / Dining / Hospitality: Deep obsidian black with champagne gold / warm bronze accents (use #f59e0b/20, #e2d9c8, amber-300 — never harsh yellow).
     * Health / Wellness: Clean whites, soft mint / emerald accents, gentle rounded cards.

3. ESSENTIAL SECTIONS WITH FLAWLESS LAYOUT:
   - Sticky Glassmorphism Header:
     * Structure: <header class="fixed top-0 left-0 right-0 z-50 backdrop-blur-xl bg-slate-950/80 border-b border-white/10">
     * Nav: <nav class="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
     * Left: Brand logo with icon and clean typography.
     * Center: Desktop navigation links with <div class="hidden md:flex items-center space-x-8 text-sm font-medium text-slate-300"> with smooth hover transitions. MUST NOT clump or bunch against the logo!
     * Right: Primary CTA button ("Get Started", "Book Now") with hover glow, plus mobile menu toggle button.
     * Mobile Menu: Full overlay with smooth toggle.
   - Hero Section:
     * Micro announcement badge: <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-indigo-500/30 bg-indigo-500/10 text-indigo-300 text-xs font-semibold mb-6">
     * High-impact Headline: text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight with gradient text accents.
     * Subheadline: text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto mb-10.
     * CTA Buttons: Primary gradient button with shadow-lg shadow-indigo-500/25, secondary glass button with border-white/15.
     * Visual Showcase: High-tech terminal mockup, live stats grid, or interactive product card.
   - About / Core Value Proposition: Authentic story with stats counters (e.g. 99.99% Uptime, 50k+ Users).
   - Interactive Bento / Feature Grid: Minimum 4–6 cards with hover-lift (hover:-translate-y-1.5 transition duration-300) and glowing gradient borders.
   - Testimonials: Authentic customer quotes with star ratings and avatar images.
   - Interactive FAQ Accordion: 4–6 questions with functional vanilla JS smooth toggle.
   - High-Converting Lead Capture Form: Name, Email, Phone/Message with modern focus states.
   - Comprehensive Footer: Logo, product links, contact info, social icons, and copyright.

4. IMAGERY:
   - Include high-resolution, relevant Unsplash photos with proper query params:
     Format: https://images.unsplash.com/photo-[PHOTO_ID]?auto=format&fit=crop&w=1200&q=80 (realistic curated Unsplash IDs).

5. INTERACTIVE JAVASCRIPT:
   - Lightweight Vanilla JS before </body> for:
     a) Mobile menu open/close.
     b) FAQ accordion toggle.
     c) Smooth anchor scroll.
     d) Lead form submission animation.

6. CRITICAL OUTPUT FORMAT:
   - Return ONLY raw HTML code. Do NOT wrap in markdown code fences like ```html or ```.
"""

SITE_EDIT_SYSTEM_PROMPT = """You are VoidPanel AI Site Architect — a world-class principal frontend engineer and UI/UX designer.
You are modifying an existing HTML website based on user instructions.
Follow the user's requested changes precisely (e.g. changing colors, updating copy, adding sections, modifying forms) while strictly adhering to Stripe/Linear-grade design aesthetics:
- Maintain proper whitespace, flawless navbar alignment (logo left, links center, CTA right), modern typography, and responsive layouts.
- Preserve all existing functional sections unless explicitly asked to remove them.
- Return ONLY the complete updated raw HTML document starting with <!DOCTYPE html> and closing with </html>, without markdown code fences.
"""


def _clean_html_response(raw_text):
    """Strips markdown code fences like ```html ... ``` if present."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


def generate_initial_website(business_name, category, description, theme, domain_name, user_identifier):
    """
    Generates a brand new complete website using Gemini Pool, saves it to AISiteProject,
    and records Revision v1.
    """
    user_prompt = f"""Create a world-class website for the following business:
- Business Name: {business_name}
- Category: {category}
- Description & Highlights: {description}
- Preferred Visual Theme: {theme}
- Domain Name: {domain_name}

Make the website feel premium, complete, and fully populated with realistic text, prices, features, and images.
Return only the complete HTML5 document.
"""

    raw_html = GeminiPoolManager.generate_content(
        prompt=user_prompt,
        system_instruction=SITE_BUILDER_SYSTEM_PROMPT,
        temperature=0.7
    )
    clean_html = _clean_html_response(raw_html)

    # Save or update AISiteProject
    project, created = AISiteProject.objects.get_or_create(
        domain=domain_name,
        defaults={
            'user_identifier': user_identifier,
            'business_name': business_name,
            'business_category': category,
            'primary_theme': theme,
            'current_html': clean_html,
            'version': 1
        }
    )

    if not created:
        project.business_name = business_name
        project.business_category = category
        project.primary_theme = theme
        project.current_html = clean_html
        project.version += 1
        project.save()

    # Record revision
    AISiteRevision.objects.create(
        project=project,
        version=project.version,
        prompt_used=f"Initial Generation: {description[:200]}",
        html_content=clean_html
    )

    return project, clean_html


def iterate_website(project_id, edit_prompt):
    """
    Applies user-requested modifications to the current project HTML.
    Creates a new revision version.
    """
    project = AISiteProject.objects.get(id=project_id)

    prompt = f"""Here is the existing HTML website for {project.business_name} ({project.domain}):
--- EXISTING HTML START ---
{project.current_html}
--- EXISTING HTML END ---

USER'S REQUESTED CHANGES:
{edit_prompt}

Please update the website according to the user's request while maintaining all responsive styling and design excellence.
Return the complete updated raw HTML.
"""

    raw_html = GeminiPoolManager.generate_content(
        prompt=prompt,
        system_instruction=SITE_EDIT_SYSTEM_PROMPT,
        temperature=0.5
    )
    updated_html = _clean_html_response(raw_html)

    project.current_html = updated_html
    project.version += 1
    project.save(update_fields=['current_html', 'version', 'updated_at'])

    AISiteRevision.objects.create(
        project=project,
        version=project.version,
        prompt_used=edit_prompt,
        html_content=updated_html
    )

    return project, updated_html


def rollback_website(project_id, target_version):
    """
    Rolls back the project to a specified past revision.
    """
    project = AISiteProject.objects.get(id=project_id)
    rev = AISiteRevision.objects.get(project=project, version=target_version)

    project.current_html = rev.html_content
    project.version += 1
    project.save(update_fields=['current_html', 'version', 'updated_at'])

    AISiteRevision.objects.create(
        project=project,
        version=project.version,
        prompt_used=f"Rollback to v{target_version}",
        html_content=rev.html_content
    )
    return project, project.current_html


def resolve_domain_document_root(domain_name, username):
    """
    Dynamically discovers the exact web document root for any domain or subdomain:
    1. Inspects the live Nginx vhost config for 'root <path>;'.
    2. Fallback to subdomain folder conventions (/home/<user>/public_html/<subdomain>).
    3. Fallback to standard primary domain (/home/<user>/public_html).
    """
    import re
    from voidplatform.config import paths

    # 1. Try reading live Nginx vhost configuration
    nginx_conf = f"/etc/nginx/sites-available/{domain_name}.conf"
    if os.path.isfile(nginx_conf):
        try:
            with open(nginx_conf, 'r', encoding='utf-8') as f:
                content = f.read()
            m = re.search(r'^\s*root\s+([^\s;]+);', content, re.MULTILINE)
            if m:
                vhost_root = m.group(1).strip()
                if '/home/' in vhost_root:
                    return vhost_root
        except Exception as e:
            logger.warning(f"Could not parse Nginx vhost root for {domain_name}: {e}")

    # 2. Check subdomain conventions
    from control.models import subdomainname, domain as domain_model
    sub_obj = subdomainname.objects.filter(name=domain_name).first()
    if sub_obj:
        sub_label = sub_obj.subdomain.split('.')[0] if '.' in sub_obj.subdomain else sub_obj.subdomain
        return os.path.join(paths.HOME_BASE, username, 'public_html', sub_label)

    dom_obj = domain_model.objects.filter(domain=domain_name).first()
    if dom_obj and not dom_obj.userdomain:
        parts = domain_name.split('.')
        if len(parts) >= 3:
            return os.path.join(paths.HOME_BASE, username, 'public_html', parts[0])

    # 3. Standard Primary domain root
    return os.path.join(paths.HOME_BASE, username, 'public_html')


def publish_website_to_domain(project, username):
    """
    Writes the active project HTML into the exact document root for the domain or subdomain.
    Creates backups of any previous index.html, index.php, or index.htm files.
    Uses sudo file operations so www-data can write across any customer account seamlessly.
    """
    import tempfile
    import subprocess

    # Target directory dynamically resolved
    target_dir = resolve_domain_document_root(project.domain, username)
    index_path = os.path.join(target_dir, 'index.html')
    backups_dir = os.path.join(target_dir, '.ai_site_backups')

    # Ensure directories exist
    subprocess.run(['sudo', 'mkdir', '-p', target_dir], check=False)
    subprocess.run(['sudo', 'mkdir', '-p', backups_dir], check=False)

    # Backup existing index.html if present
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    if os.path.isfile(index_path):
        bak_file = os.path.join(backups_dir, f'index_backup_{timestamp}.html')
        subprocess.run(['sudo', 'cp', index_path, bak_file], check=False)

    # If conflicting index.php or index.htm is present (e.g. placeholder pages), archive to backups
    # so Nginx's 'index index.php index.html' immediately prioritizes the newly published index.html
    for old_ext in ['php', 'htm']:
        conflicting_file = os.path.join(target_dir, f'index.{old_ext}')
        if os.path.isfile(conflicting_file):
            bak_conflict = os.path.join(backups_dir, f'index_backup_{timestamp}.{old_ext}')
            subprocess.run(['sudo', 'mv', conflicting_file, bak_conflict], check=False)

    # Write new HTML via safe temporary file + sudo cp (bypasses www-data direct file ownership limitations)
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, prefix='voidpanel_ai_') as tmp:
            tmp.write(project.current_html)
            tmp_path = tmp.name

        # Copy to production destination with sudo
        subprocess.run(['sudo', 'cp', tmp_path, index_path], check=True)
        # Set proper ownership and permissions
        subprocess.run(['sudo', 'chown', f'{username}:{username}', index_path], check=False)
        subprocess.run(['sudo', 'chmod', '644', index_path], check=False)
        subprocess.run(['sudo', 'chown', '-R', f'{username}:{username}', backups_dir], check=False)
        # Ensure target directory is traversable
        subprocess.run(['sudo', 'chmod', '755', target_dir], check=False)

        try:
            os.remove(tmp_path)
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Failed writing index.html for {username} at {index_path}: {e}")
        return False, f"Disk write failed: {str(e)}"

    # Update project state
    project.is_published = True
    project.published_at = timezone.now()
    project.save(update_fields=['is_published', 'published_at'])

    return True, f"Successfully published to https://{project.domain}"
