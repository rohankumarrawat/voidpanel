from django.urls import path
from . import views

urlpatterns = [
    path('api/burn/create/', views.create_burn_message, name='create_burn_message'),
    path('secret/<str:token>/', views.view_burn_message, name='view_burn_message'),
    path('api/voidmask/generate/', views.generate_voidmask_alias, name='generate_voidmask_alias'),
]
