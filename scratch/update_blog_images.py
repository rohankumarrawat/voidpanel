import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voidpanel.settings")
sys.path.insert(0, "/home/voidonyx/voidonyx")
django.setup()

from data.models import BlogPost

updates = {
    24: "blog_images/voidpanel_2026_migration_banner.png",
    25: "blog_images/professional_email_domain_guide.png",
    27: "blog_images/b2b_lead_generation_2026.png",
    28: "blog_images/business_automation_growth.png",
    2:  "blog_images/ditching_cpanel_for_voidpanel.png",
}

print("=== STARTING DB UPDATE ===")
for pid, img_path in updates.items():
    try:
        p = BlogPost.objects.get(id=pid)
        p.featured_image = img_path
        p.save()
        print(f"SUCCESS: Updated Post #{pid} ({p.slug}) -> {img_path}")
    except Exception as e:
        print(f"ERROR on Post #{pid}: {e}")

print("\n=== CURRENT STATUS OF ALL PUBLISHED BLOG POSTS ===")
posts = BlogPost.objects.filter(status="published").order_by("-id")
for p in posts:
    img = str(p.featured_image) if p.featured_image else "MISSING"
    title = p.title.encode("ascii", "ignore").decode("ascii")
    print(f"ID: {p.id:<2} | Image: {img:<52} | Title: {title[:40]}")
