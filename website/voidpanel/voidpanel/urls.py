from django.contrib import admin
from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index),
    path('docs/', views.docs),
    path('web-hosting/', views.pricing),
    path('web-hosting/order-summary/', views.order_summary),
    path('pricing/', views.pricing),
    path('pricing/order-summary/', views.order_summary),
    path('blog/', views.blog),
    path('blogs/', views.blogs),
    path('addssl/', views.ssl),
    path('cloud-computing/', views.blog2),
    path('voidpanel-info/', views.voidpanelinfo),
    path('alternative-of-cpanel/', views.blog3),
    path('aboutus/', views.aboutus),
    path('db/', views.db),
    path('positive/', views.positive, name='positive'),
    path('negative/', views.negative, name='negative'),
    path('ai/', include('chatting.urls')),
    path('overview/', views.overview),
    path('chpass/', views.chpass),
    path('addweb/', views.addweb),
    path('notifications/', views.notifications),
    path('latest_messages/', views.latest_messages),
    path('version_name/', views.update),
    path('admindocs/', views.admindocs),
    path('clientdocs/', views.clientdocs),
    path('api/increment/', views.increment_number, name='increment-number'),
    path('login/', views.loginn),
    path('logout/', views.logout_view),
    path('register/', views.register),

    # ── Client Portal ──────────────────────────────────────────────────────────
    path('portal/', views.portal),
    path('portal/ticket/new/', views.portal_ticket_new, name='portal_ticket_new'),
    path('portal/ticket/<int:ticket_id>/', views.portal_ticket_detail, name='portal_ticket_detail'),
    path('portal/invoice/<int:inv_id>/pay/', views.invoice_pay, name='invoice_pay'),
    path('portal/order-complete/', views.order_complete, name='order_complete'),

    # ── Cart & Checkout ────────────────────────────────────────────────────────
    path('cart/<slug:slug>/', views.cart_config, name='cart_config'),

    # ── Super Admin ────────────────────────────────────────────────────────────
    path('super-admin/', views.super_admin_portal),
    path('super-admin/servers/', views.super_admin_servers),
    path('super-admin/staff/', views.super_admin_staff),
    path('super-admin/roles/', views.super_admin_roles),
    path('super-admin/emails/', views.super_admin_emails),
    path('super-admin/hosting/', views.super_admin_hosting),
    path('super-admin/signals/', views.super_admin_signals),
    path('super-admin/clients/', views.super_admin_clients),
    path('super-admin/billing/', views.super_admin_billing),
    path('super-admin/tickets/', views.super_admin_tickets),
    path('super-admin/tickets/<int:ticket_id>/', views.super_admin_ticket_detail),

    # ── Blog / Legacy ──────────────────────────────────────────────────────────
    path('blog1/', views.blog1),
    path('addemail/', views.addemail),
    path('whmcs/', views.whmcs),
    path('whmcs/module/', views.whmcs_module),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
