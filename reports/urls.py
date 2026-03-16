from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Report Views
    path('', views.index, name='index'),
    path('rental/', views.rental_report, name='rental_report'),
    path('harvest/', views.harvest_report, name='harvest_report'),
    path('financial/', views.financial_summary, name='financial_summary'),
    path('machine-usage/', views.machine_usage_report, name='machine_usage_report'),
    path('membership/', views.membership_report, name='membership_report'),
    
    # Sector Reports (Phase 6)
    path('sectors/<int:pk>/member-list/', views.sector_member_list_report, name='sector_member_list'),
    path('sectors/<int:pk>/summary/', views.sector_summary_report, name='sector_summary'),
    path('sectors/comparison/', views.sector_comparison_report, name='sector_comparison'),
    
    # Export Endpoints
    path('rental/export/', views.export_rental_report, name='export_rental_report'),
    path('harvest/export/', views.export_harvest_report, name='export_harvest_report'),
    path('financial/export/', views.export_financial_report, name='export_financial_report'),
]
