from django.urls import path
from . import views
from . import admin_views
from . import calendar_views
from . import rental_calendar_view
from . import operator_views
from . import operator_management_views  # For redirect from old URLs to new system
from . import operator_notification_views
from . import operator_decision_views

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
    path('rentals/<int:pk>/confirmation/print/', views.rental_confirmation_print, name='rental_confirmation_print'),
    path('rentals/<int:pk>/receipt/', views.rental_confirmation_print, name='rental_receipt'),
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
    path('admin/rental/<int:rental_id>/start-operation/', admin_views.start_equipment_operation, name='start_equipment_operation'),
    path('admin/rental/<int:rental_id>/harvest-report/', admin_views.submit_harvest_report, name='submit_harvest_report'),
    path('admin/rental/<int:rental_id>/confirm-rice-received/', admin_views.confirm_rice_received, name='confirm_rice_received'),
    path('admin/rental/<int:rental_id>/verify-online-payment/', admin_views.verify_online_payment, name='verify_online_payment'),
    path('admin/rental/<int:rental_id>/record-face-to-face-payment/', admin_views.record_face_to_face_payment, name='record_face_to_face_payment'),
    path('admin/rental/<int:rental_id>/assign-operator/', operator_views.assign_operator, name='assign_operator'),
    path('admin/rental/<int:rental_id>/payment-proof/', admin_views.view_payment_proof, name='view_payment_proof'),
    path('admin/verify-payment/<int:rental_id>/', admin_views.verify_payment_ajax, name='verify_payment_ajax'),
    path('admin/conflicts/', admin_views.admin_conflicts_report, name='admin_conflicts_report'),
    path('admin/bulk-approve/', admin_views.bulk_approve_rentals, name='bulk_approve_rentals'),
    path('admin/bulk-delete/', admin_views.bulk_delete_rentals, name='bulk_delete_rentals'),
    path('admin/rental/<int:rental_id>/complete-early/', admin_views.admin_complete_rental_early, name='admin_complete_rental_early'),

    # Operator dashboard and clean navigation
    path('operator/dashboard/', operator_views.operator_dashboard, name='operator_dashboard'),
    path('operator/jobs/', operator_views.operator_all_jobs, name='operator_jobs'),
    path('operator/jobs/<int:rental_id>/', operator_views.operator_job_detail, name='operator_job_detail'),
    path('operator/work/', operator_views.operator_ongoing_jobs, name='operator_work'),
    path('operator/jobs/all/', operator_views.operator_all_jobs, name='operator_all_jobs'),
    path('operator/jobs/ongoing/', operator_views.operator_ongoing_jobs, name='operator_ongoing_jobs'),
    path('operator/jobs/awaiting-harvest/', operator_views.operator_awaiting_harvest, name='operator_awaiting_harvest'),
    path('operator/jobs/completed/', operator_views.operator_completed_jobs, name='operator_completed_jobs'),
    path('operator/payments/in-kind/', operator_views.operator_in_kind_payments, name='operator_in_kind_payments'),
    path('operator/machines/', operator_views.operator_view_machines, name='operator_view_machines'),
    path('operator/notifications/', operator_notification_views.operator_notifications, name='operator_notifications'),
    path('operator/notifications/<int:notification_id>/', operator_notification_views.operator_notification_detail, name='operator_notification_detail'),
    path('operator/rental/<int:rental_id>/update/', operator_views.update_operator_job, name='update_operator_job'),
    path('operator/rental/<int:rental_id>/harvest/', operator_views.submit_operator_harvest, name='submit_operator_harvest'),
    path('operator/rental/<int:rental_id>/decision/', operator_decision_views.operator_decision_form, name='operator_decision_form'),
    path('operator/rental/<int:rental_id>/make-decision/', operator_decision_views.operator_make_decision, name='operator_make_decision'),
    
    # Operator overview (admin)
    path('operators/overview/', admin_views.operator_overview, name='operator_overview'),
    
    # OLD Operator Management URLs - REDIRECT to new system
    # These URLs redirect to the new operator overview page with helpful messages
    path('operators/', operator_management_views.operator_list, name='operator_list'),
    path('operators/add/', operator_management_views.operator_add, name='operator_add'),
    path('operators/<int:operator_id>/', operator_management_views.operator_detail, name='operator_detail'),
    path('operators/<int:operator_id>/edit/', operator_management_views.operator_edit, name='operator_edit'),
    path('operators/<int:operator_id>/delete/', operator_management_views.operator_delete, name='operator_delete'),
    path('operators/<int:operator_id>/assign-machine/', operator_management_views.operator_assign_machine, name='operator_assign_machine'),
    
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
    path('rice-mill-appointments/<int:pk>/receipt/', views.ricemill_appointment_receipt, name='ricemill_appointment_receipt'),
] 
