"""
URL configuration for bufia project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from bufia.views import payment_views

urlpatterns = [
    path('activity-logs/', include('activity_logs.urls')),
    
    # Admin Payment Management URLs (must come before admin/ to avoid conflict)
    path('admin/payments/', payment_views.admin_payment_list, name='admin_payment_list'),
    path('admin/payments/<int:payment_id>/', payment_views.admin_payment_detail, name='admin_payment_detail'),
    path('admin/payments/export/', payment_views.export_payments, name='export_payments'),
    
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('users.urls')),
    path('machines/', include('machines.urls')),
    path('notifications/', include('notifications.urls')),
    path('reports/', include('reports.urls')),
    path('irrigation/', include('irrigation.urls')),
    path('general-reports/', include('general_reports.urls')),
    
    # Payment URLs
    path('payment/rental/<int:rental_id>/', payment_views.create_rental_payment, name='create_rental_payment'),
    path('payment/irrigation/<int:irrigation_id>/', payment_views.create_irrigation_payment, name='create_irrigation_payment'),
    path('payment/appointment/<int:appointment_id>/', payment_views.create_appointment_payment, name='create_appointment_payment'),
    path('payment/membership/<int:membership_id>/', payment_views.create_membership_payment, name='create_membership_payment'),
    path('payment/success/', payment_views.payment_success, name='payment_success'),
    path('payment/cancelled/', payment_views.payment_cancelled, name='payment_cancelled'),
    path('payment/webhook/', payment_views.stripe_webhook, name='stripe_webhook'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
