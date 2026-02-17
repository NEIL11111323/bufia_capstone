from django.urls import path
from . import views
from . import admin_views
from . import calendar_views
from . import rental_calendar_view

app_name = 'machines'

urlpatterns = [
    # Calendar API endpoints
    path('api/calendar/<int:machine_id>/events/', calendar_views.machine_calendar_events, name='machine_calendar_events'),
    path('api/calendar/all-events/', calendar_views.all_machines_calendar_events, name='all_machines_calendar_events'),
    path('api/check-availability/', calendar_views.check_date_availability, name='check_date_availability'),
    
    # Calendar-based rental creation (NEW)
    path('rentals/create-with-calendar/', rental_calendar_view.rental_create_with_calendar, name='rental_create_calendar'),
    path('rentals/create-with-calendar/<int:machine_pk>/', rental_calendar_view.rental_create_with_calendar, name='rental_create_calendar_with_machine'),
    
    # Machine views
    path('', views.MachineListView.as_view(), name='machine_list'),
    path('<int:pk>/', views.MachineDetailView.as_view(), name='machine_detail'),
    path('create/', views.MachineCreateView.as_view(), name='machine_create'),
    path('<int:pk>/edit/', views.MachineUpdateView.as_view(), name='edit_machine'),
    path('<int:pk>/delete/', views.machine_delete_view, name='delete_machine'),
    path('<int:machine_pk>/rent/', views.RentalCreateView.as_view(), name='rent_machine'),
    path('<int:pk>/debug-images/', views.debug_machine_images, name='debug_machine_images'),
    
    # Rental views - User rental history
    path('rentals/', views.rental_list, name='rental_list'),
    path('rentals/payment-success/', views.payment_success, name='payment_success'),
    path('rentals/create/', views.RentalCreateView.as_view(), name='rental_create'),
    path('rentals/create/<int:machine_id>/', views.RentalCreateView.as_view(), name='rental_create_for_machine'),
    path('rentals/<int:pk>/confirmation/', views.rental_confirmation, name='rental_confirmation'),
    path('rentals/<int:rental_id>/upload-proof/', views.upload_payment_proof, name='upload_payment_proof'),
    path('rentals/<int:pk>/update/', views.RentalUpdateView.as_view(), name='rental_update'),
    path('rentals/<int:pk>/delete/', views.RentalDeleteView.as_view(), name='rental_delete'),
    path('rentals/<int:pk>/approve/', views.approve_rental, name='rental_approve'),
    path('rentals/<int:pk>/reject/', views.rental_reject, name='rental_reject'),
    path('rentals/<int:pk>/slip/', views.rental_slip, name='rental_slip'),
    path('rentals/<int:pk>/', views.RentalDetailView.as_view(), name='rental_detail'),
    
    # Admin rental management
    path('admin/rentals/create/', views.admin_rental_create, name='admin_rental_create'),
    path('admin/rentals/create/<int:machine_pk>/', views.admin_rental_create, name='admin_rental_create_for_machine'),
    
    # Admin Dashboard & Approval
    path('admin/dashboard/', admin_views.admin_rental_dashboard, name='admin_rental_dashboard'),
    path('admin/rental/<int:rental_id>/approve/', admin_views.admin_approve_rental, name='admin_approve_rental'),
    path('admin/rental/<int:rental_id>/payment-proof/', admin_views.view_payment_proof, name='view_payment_proof'),
    path('admin/verify-payment/<int:rental_id>/', admin_views.verify_payment_ajax, name='verify_payment_ajax'),
    path('admin/conflicts/', admin_views.admin_conflicts_report, name='admin_conflicts_report'),
    path('admin/bulk-approve/', admin_views.bulk_approve_rentals, name='bulk_approve_rentals'),
    path('admin/bulk-delete/', admin_views.bulk_delete_rentals, name='bulk_delete_rentals'),
    
    # Maintenance URLs
    path('maintenance/', views.maintenance_list, name='maintenance_list'),
    path('maintenance/create/', views.maintenance_create, name='maintenance_create'),
    path('maintenance/create/<int:machine_pk>/', views.maintenance_create, name='maintenance_create_for_machine'),
    path('maintenance/<int:pk>/', views.maintenance_detail, name='maintenance_detail'),
    path('maintenance/<int:pk>/update/', views.maintenance_update, name='maintenance_update'),
    path('maintenance/<int:pk>/complete/', views.maintenance_complete, name='maintenance_complete'),
    path('maintenance/<int:pk>/delete/', views.maintenance_delete, name='maintenance_delete'),
    
    # Price History URLs
    path('<int:machine_pk>/price-history/create/', views.price_history_create, name='price_history_create'),
    
    # Rice Mill Appointment URLs
    path('rice-mill-appointments/', views.RiceMillAppointmentListView.as_view(), name='ricemill_appointment_list'),
    path('rice-mill-appointments/<int:pk>/', views.RiceMillAppointmentDetailView.as_view(), name='ricemill_appointment_detail'),
    path('rice-mill-appointments/create/', views.RiceMillAppointmentCreateView.as_view(), name='ricemill_appointment_create'),
    path('rice-mill-appointments/create/<int:machine_id>/', views.RiceMillAppointmentCreateView.as_view(), name='ricemill_appointment_create_for_machine'),
    path('rice-mill-appointments/<int:pk>/update/', views.RiceMillAppointmentUpdateView.as_view(), name='ricemill_appointment_update'),
    path('rice-mill-appointments/<int:pk>/delete/', views.RiceMillAppointmentDeleteView.as_view(), name='ricemill_appointment_delete'),
    path('rice-mill-appointments/<int:pk>/approve/', views.approve_appointment, name='ricemill_appointment_approve'),
    path('rice-mill-appointments/<int:pk>/reject/', views.reject_appointment, name='ricemill_appointment_reject'),
    path('rice-mill-appointments/<int:pk>/pending/', views.ricemill_appointment_pending, name='ricemill_appointment_pending'),
] 