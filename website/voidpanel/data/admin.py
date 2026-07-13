from django.contrib import admin
from .models import (
    CustomerProfile,
    HostingService,
    Installed,
    Invoice,
    Message,
    OutboundEmailProfile,
    PortalActivity,
    StaffProfile,
    StaffRole,
    SupportTicket,
    admindocumentation,
    clientdocumentation,
    negative_review,
    positive_review,
    updates,
    ResellerPricingSettings,
    MarketingService,
    FundTransaction,
    ChipTransaction,
    HostingPricingSettings,
)

# Register your models here.
admin.site.register(Message)
admin.site.register(Installed)
admin.site.register(clientdocumentation)
admin.site.register(admindocumentation)
admin.site.register(updates)
admin.site.register(positive_review)
admin.site.register(negative_review)
admin.site.register(CustomerProfile)
admin.site.register(HostingService)
admin.site.register(Invoice)
admin.site.register(SupportTicket)
admin.site.register(PortalActivity)
admin.site.register(StaffRole)
admin.site.register(StaffProfile)
admin.site.register(OutboundEmailProfile)
admin.site.register(FundTransaction)
admin.site.register(ChipTransaction)

from .models import GlobalEmailTemplate
admin.site.register(GlobalEmailTemplate)

@admin.register(ResellerPricingSettings)
class ResellerPricingSettingsAdmin(admin.ModelAdmin):
    list_display = ('title', 'base_price_monthly', 'updated_at')

@admin.register(HostingPricingSettings)
class HostingPricingSettingsAdmin(admin.ModelAdmin):
    list_display = ('title', 'signup_bonus_chips', 'credits_per_rupee', 'updated_at')

@admin.register(MarketingService)
class MarketingServiceAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan_name', 'status', 'billing_cycle', 'created_at')
    list_filter = ('status', 'billing_cycle', 'plan_name')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('leads_stored', 'emails_sent_this_month', 'ai_copies_used_this_month')
