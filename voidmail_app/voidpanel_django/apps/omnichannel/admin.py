from django.contrib import admin
from .models import VipContact, OmnichannelLog

@admin.register(VipContact)
class VipContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'whatsapp_number', 'enable_whatsapp_alert', 'created_at')
    search_fields = ('name', 'email', 'whatsapp_number')

@admin.register(OmnichannelLog)
class OmnichannelLogAdmin(admin.ModelAdmin):
    list_display = ('channel', 'direction', 'recipient', 'status', 'created_at')
    list_filter = ('channel', 'direction', 'status')
