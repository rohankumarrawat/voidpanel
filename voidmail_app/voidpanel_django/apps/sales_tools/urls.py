from django.urls import path
from . import views

urlpatterns = [
    path('t/pixel/<str:token>.png', views.track_pixel_view, name='track_pixel'),
    path('t/link/<str:token>/', views.track_link_redirect, name='track_link'),
    path('t/thread/<str:token>/', views.view_shared_thread, name='shared_thread'),
    path('api/snippets/', views.snippets_api, name='snippets_api'),
]
