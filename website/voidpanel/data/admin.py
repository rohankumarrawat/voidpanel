from django.contrib import admin
from .models import positive_review,negative_review,Message,Installed,clientdocumentation,admindocumentation,updates

# Register your models here.
admin.site.register(Message)
admin.site.register(Installed)
admin.site.register(clientdocumentation)
admin.site.register(admindocumentation)
admin.site.register(updates)
admin.site.register(positive_review)
admin.site.register(negative_review)
