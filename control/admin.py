from django.contrib import admin

# Register your models here.
from control.models import (
    mernname, phpextentions, portnumber, pythonname, ftp, phpversion,
    quick, package, user, LoginActivity, domain, allemail, cron,
    subdomainname, redir, firewall, ftpaccount, SavedSEODomain,
    VoidMailUpgradeLead, VoidMailWhitelistedDomain, VoidMailWhitelistIP,
    EmailDeviceToken, VoidMailAppLogin,
)

@admin.register(VoidMailUpgradeLead)
class VoidMailUpgradeLeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'domain', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'email', 'phone', 'domain')
    readonly_fields = ('created_at', 'updated_at', 'caller_ip')
    actions = ['whitelist_selected_domains_and_enable_ai']

    @admin.action(description='✨ Whitelist selected domains & Enable VoidMail AI')
    def whitelist_selected_domains_and_enable_ai(self, request, queryset):
        count = 0
        for lead in queryset:
            VoidMailWhitelistedDomain.objects.update_or_create(
                domain=lead.domain.lower(),
                defaults={
                    'is_active': True,
                    'lead': lead,
                    'notes': f'Whitelisted via Superadmin for lead {lead.name} ({lead.email})',
                }
            )
            count += 1
        queryset.update(status='whitelisted')
        self.message_user(
            request,
            f"Successfully whitelisted {count} domain(s) and activated VoidMail AI!"
        )


@admin.register(VoidMailWhitelistedDomain)
class VoidMailWhitelistedDomainAdmin(admin.ModelAdmin):
    list_display = ('domain', 'is_active', 'lead', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('domain', 'notes')
    list_editable = ('is_active',)


@admin.register(VoidMailWhitelistIP)
class VoidMailWhitelistIPAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'domain', 'label', 'created_at')
    search_fields = ('ip_address', 'domain', 'label')


@admin.register(EmailDeviceToken)
class EmailDeviceTokenAdmin(admin.ModelAdmin):
    list_display = ('email', 'domain', 'platform', 'device_name', 'is_active', 'updated_at')
    list_filter = ('platform', 'is_active')
    search_fields = ('email', 'domain', 'device_name', 'fcm_token')


@admin.register(VoidMailAppLogin)
class VoidMailAppLoginAdmin(admin.ModelAdmin):
    list_display = ('email', 'domain', 'platform', 'login_method', 'ip_address', 'logged_in_at')
    list_filter = ('domain', 'platform', 'login_method', 'logged_in_at')
    search_fields = ('email', 'domain', 'ip_address', 'device_name')
    readonly_fields = ('email', 'domain', 'platform', 'device_name', 'ip_address', 'login_method', 'logged_in_at')
    date_hierarchy = 'logged_in_at'


admin.site.register(quick)
admin.site.register(package)
admin.site.register(user)
admin.site.register(LoginActivity)
admin.site.register(domain)
admin.site.register(allemail)
admin.site.register(cron)
admin.site.register(subdomainname)
admin.site.register(redir)
admin.site.register(phpversion)
admin.site.register(firewall)
admin.site.register(ftp)
admin.site.register(ftpaccount)
admin.site.register(pythonname)
admin.site.register(portnumber)
admin.site.register(phpextentions)
admin.site.register(mernname)
admin.site.register(SavedSEODomain)