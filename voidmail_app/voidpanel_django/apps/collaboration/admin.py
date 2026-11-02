from django.contrib import admin
from .models import CalendarEvent, BookingSlot, VoidDoc, SignatureDocument, FormDefinition

@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_time', 'end_time', 'created_at')

@admin.register(BookingSlot)
class BookingSlotAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'duration_minutes', 'is_active')

@admin.register(VoidDoc)
class VoidDocAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_public', 'updated_at', 'created_at')

@admin.register(SignatureDocument)
class SignatureDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'signatory_email', 'is_signed', 'signed_at', 'created_at')

@admin.register(FormDefinition)
class FormDefinitionAdmin(admin.ModelAdmin):
    list_display = ('title', 'delivery_email', 'submissions_count', 'created_at')
