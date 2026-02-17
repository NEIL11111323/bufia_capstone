from django.urls import path
from . import views

app_name = 'irrigation'

urlpatterns = [
    # Farmer URLs
    path('request/', views.irrigation_request_create, name='irrigation_request_create'),
    path('requests/', views.irrigation_request_list, name='irrigation_request_list'),
    path('request/<int:pk>/', views.irrigation_request_detail, name='irrigation_request_detail'),
    path('request/<int:pk>/cancel/', views.irrigation_request_cancel, name='irrigation_request_cancel'),
    path('history/', views.user_irrigation_request_history, name='user_irrigation_request_history'),
    
    # Water Tender URLs
    path('water-tender/requests/', views.water_tender_irrigation_request_list, name='water_tender_irrigation_request_list'),
    path('water-tender/request/<int:pk>/', views.water_tender_irrigation_request_detail, name='water_tender_irrigation_request_detail'),
    
    # Admin URLs
    path('admin/requests/', views.admin_irrigation_request_list, name='admin_irrigation_request_list'),
    path('admin/request/create/', views.admin_irrigation_request_create, name='admin_irrigation_request_create'),
    path('admin/request/<int:pk>/', views.admin_irrigation_request_detail, name='admin_irrigation_request_detail'),
    path('admin/history/', views.admin_irrigation_request_history, name='admin_irrigation_request_history'),
] 