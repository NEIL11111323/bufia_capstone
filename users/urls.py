from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/photo/update/', views.update_profile_photo, name='update_profile_photo'),
    path('profile/password/change/', views.change_password, name='change_password'),
    path('profile/membership/submit/', views.submit_membership_form, name='submit_membership_form'),
    path('profile/membership/slip/', views.membership_slip, name='membership_slip'),
    path('profile/membership/info/', views.view_membership_info, name='view_membership_info_self'),
    path('profile/membership/info/<int:user_id>/', views.view_membership_info, name='view_membership_info_user'),
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.create_user, name='create_user'),
    path('users/<int:pk>/edit/', views.edit_user, name='edit_user'),
    path('users/<int:pk>/delete/', views.delete_user, name='delete_user'),
    path('users/<int:pk>/verify/', views.verify_user, name='verify_user'),
    path('users/<int:pk>/reject/', views.reject_verification, name='reject_verification'),
    path('members/masterlist/', views.members_masterlist, name='members_masterlist'),
    path('members/export/csv/', views.export_members_csv, name='export_members_csv'),
    path('members/export/pdf/', views.export_members_pdf, name='export_members_pdf'),
    
    # Verification requests management
    path('verification-requests/', views.verification_requests, name='verification_requests'),
    
    # Sector management
    path('sectors/', views.sector_list, name='sector_list'),
    path('sectors/create/', views.create_sector, name='create_sector'),
    path('sectors/<int:pk>/edit/', views.edit_sector, name='edit_sector'),
    path('sectors/<int:pk>/delete/', views.delete_sector, name='delete_sector'),
    
    # API endpoint for user profile data
    path('api/user/<int:user_id>/profile/', views.get_user_profile_data, name='get_user_profile_data'),
] 