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
