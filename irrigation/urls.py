from django.urls import path
from . import views

app_name = 'irrigation'

urlpatterns = [
    # Farmer URLs
    path('', views.irrigation_request_list, name='irrigation_list'),
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
    path('admin/request/<int:pk>/edit/', views.admin_irrigation_request_edit, name='admin_irrigation_request_edit'),
    path('admin/request/<int:pk>/', views.admin_irrigation_request_detail, name='admin_irrigation_request_detail'),
    path('admin/request/<int:pk>/assign-farmers/', views.admin_irrigation_assign_farmers, name='admin_irrigation_assign_farmers'),
    path('admin/request/<int:pk>/generate-billing/', views.admin_irrigation_generate_billing, name='admin_irrigation_generate_billing'),
    path('admin/request/<int:pk>/close-season/', views.admin_irrigation_close_season, name='admin_irrigation_close_season'),
    path('admin/record/<int:pk>/confirm-payment/', views.admin_irrigation_confirm_payment, name='admin_irrigation_confirm_payment'),
    path('admin/history/', views.admin_irrigation_request_history, name='admin_irrigation_request_history'),
] 
