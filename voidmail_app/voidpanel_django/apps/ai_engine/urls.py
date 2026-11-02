from django.urls import path
from . import views

urlpatterns = [
    path('api/smart-reply/', views.generate_smart_reply, name='ai_smart_reply'),
    path('api/summarize/', views.summarize_thread, name='ai_summarize'),
    path('api/action-items/', views.extract_action_items, name='ai_action_items'),
    path('api/polish-draft/', views.polish_email_draft, name='ai_polish_draft'),
    path('api/generate-html-template/', views.generate_html_template, name='ai_generate_html_template'),
    path('api/generate-subject/', views.generate_subject_line, name='ai_generate_subject'),
    path('api/ai-prioritize-emails/', views.classify_emails_priority, name='ai_classify_priority'),
    path('api/ai-upgrade-request/', views.request_ai_upgrade_api, name='ai_upgrade_request'),
    path('api/ai-access/request-upgrade/', views.request_ai_upgrade_api, name='ai_request_upgrade'),
    path('api/ai-access/status/', views.get_ai_status_api, name='ai_get_status'),
    path('api/analyze-crm-lead/', views.api_analyze_crm_lead, name='ai_analyze_crm_lead'),
]
