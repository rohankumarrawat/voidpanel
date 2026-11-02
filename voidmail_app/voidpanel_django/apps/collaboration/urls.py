from django.urls import path
from . import views

urlpatterns = [
    # 1. 1-Click Video Meetings (VoidMeet Sovereign Video)
    path('api/meet/create/', views.generate_voidmeet_room, name='generate_voidmeet_room'),
    path('meet/<str:room_id>/', views.voidmeet_room_view, name='voidmeet_room'),
    path('api/meet/<str:room_id>/signal/', views.voidmeet_signaling_api, name='voidmeet_signal'),

    # 2. Public Booking Calendar (https://mail.voidonyx.in/book/<username>/)
    path('book/<str:username>/', views.public_booking_page, name='public_booking_page'),
    path('book/<str:username>/slots/', views.get_available_slots_api, name='booking_slots_api'),
    path('book/<str:username>/submit/', views.submit_booking_api, name='booking_submit_api'),

    # 3. Digital Signatures (VoidSign)
    path('sign/<str:token>/', views.sign_document_view, name='sign_document'),
]
