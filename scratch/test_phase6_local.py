import sys
import os

sys.path.insert(0, '/Users/rohan/Desktop/voidpanel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')

import django
django.setup()

from control.seo_engine import (
    compute_readability_score,
    audit_images,
    analyze_social_preview,
    build_internal_link_graph,
    compare_domains_seo,
    analyze_domain_seo
)

print("1. Testing compute_readability_score...")
sample_html = """
<!DOCTYPE html>
<html>
<head>
  <title>Fast VoidPanel - The Ultimate Cloud & Hosting Management Panel</title>
  <meta name="description" content="Experience lightning-fast cloud server management, DNS routing, and website control with VoidPanel.">
  <meta property="og:title" content="Fast VoidPanel - The Ultimate Cloud Control">
  <meta property="og:description" content="Experience lightning-fast cloud server management with VoidPanel.">
  <meta property="og:image" content="https://voidpanel.com/static/og-image.png">
  <meta name="twitter:card" content="summary_large_image">
</head>
<body>
  <h1>Welcome to VoidPanel</h1>
  <p>VoidPanel is an enterprise cloud and server management panel. It enables web developers, system administrators, and digital agencies to deploy high performance web servers seamlessly.</p>
  <p>With our automated SSL certificate provisioning, comprehensive real-time SEO intelligence suite, and one-click container deployments, managing modern web infrastructure has never been easier or faster.</p>
  <img src="/static/img/hero.png" alt="VoidPanel Dashboard Interface" width="1200" height="630" loading="lazy">
  <img src="https://voidpanel.com/banner.jpg">
  <a href="/features">Features</a>
  <a href="/pricing">Pricing</a>
  <a href="/docs">Documentation</a>
</body>
</html>
"""

r = compute_readability_score(sample_html)
print("Readability Result:", r)
assert r["status"] == "ok"
assert r["flesch_reading_ease"] > 0

print("\n2. Testing audit_images...")
img_aud = audit_images(sample_html, "https://voidpanel.com")
print("Image Audit Result:", {k: v for k, v in img_aud.items() if k != "images"})
assert img_aud["status"] == "ok"
assert img_aud["total_images"] == 2
assert img_aud["missing_alt_count"] == 1

print("\n3. Testing analyze_social_preview...")
sp = analyze_social_preview(sample_html, "voidpanel.com")
print("Social Preview Result:", {k: v for k, v in sp.items() if k != "checks"})
assert sp["status"] == "ok"
assert sp["tags"]["og_title"] == "Fast VoidPanel - The Ultimate Cloud Control"

print("\n4. Testing compare_domains_seo...")
cmp_res = compare_domains_seo(["voidpanel.com", "github.com"])
print("Multi-Domain Comparison Winner:", cmp_res.get("overall_winner"))
print("Scores:", cmp_res.get("overall_scores"))
assert cmp_res["status"] == "success"
assert len(cmp_res["domains"]) == 2

print("\n5. Testing build_internal_link_graph...")
graph_res = build_internal_link_graph("voidpanel.com", max_pages=3)
print("Link Graph Nodes:", graph_res.get("total_nodes"), "Edges:", graph_res.get("total_edges"))
assert graph_res["status"] == "success"

print("\nALL PHASE 6 ENGINES PASSED SUCCESSFULLY!")
