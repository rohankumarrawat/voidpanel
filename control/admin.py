from django.contrib import admin

# Register your models here.
from control.models import mernname,phpextentions,portnumber,pythonname,ftp,phpversion,quick,package,user,LoginActivity,domain,allemail,cron,subdomainname,redir,firewall,ftpaccount
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