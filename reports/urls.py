from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Report Views
    path('', views.index, name='index'),
    path('rental/', views.rental_report, name='rental_report'),
    path('harvest/', views.harvest_report, name='harvest_report'),
    path('rice-sales/', views.rice_sales_report, name='rice_sales_report'),
    path('rice-store/', views.rice_store, name='rice_store'),
    path('financial/', views.financial_summary, name='financial_summary'),
    path('machine-usage/', views.machine_usage_report, name='machine_usage_report'),
    path('machine-usage/<int:pk>/', views.machine_usage_detail, name='machine_usage_detail'),
    path('membership/', views.membership_report, name='membership_report'),
    path('membership/<int:pk>/proof/', views.membership_proof_detail, name='membership_proof_detail'),
    
    # Sector Reports (Phase 6)
    path('sectors/<int:pk>/member-list/', views.sector_member_list_report, name='sector_member_list'),
    path('sectors/<int:pk>/summary/', views.sector_summary_report, name='sector_summary'),
    path('sectors/comparison/', views.sector_comparison_report, name='sector_comparison'),
    
    # Export Endpoints
    path('rental/export/', views.export_rental_report, name='export_rental_report'),
    path('rental/export/excel/', views.export_rental_report_excel, name='export_rental_report_excel'),
    path('rental/export/pdf/', views.export_rental_report_pdf, name='export_rental_report_pdf'),
    path('harvest/export/', views.export_harvest_report, name='export_harvest_report'),
    path('harvest/export/excel/', views.export_harvest_report_excel, name='export_harvest_report_excel'),
    path('harvest/export/pdf/', views.export_harvest_report_pdf, name='export_harvest_report_pdf'),
    path('financial/export/', views.export_financial_report, name='export_financial_report'),
    path('financial/export/excel/', views.export_financial_report_excel, name='export_financial_report_excel'),
    path('financial/export/pdf/', views.export_financial_report_pdf, name='export_financial_report_pdf'),
    path('machine-usage/export/excel/', views.export_machine_usage_report_excel, name='export_machine_usage_report_excel'),
    path('machine-usage/export/pdf/', views.export_machine_usage_report_pdf, name='export_machine_usage_report_pdf'),
    path('membership/export/excel/', views.export_membership_report_excel, name='export_membership_report_excel'),
    path('membership/export/pdf/', views.export_membership_report_pdf, name='export_membership_report_pdf'),
]
