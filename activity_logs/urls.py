from django.urls import path
from . import views

app_name = 'activity_logs'

urlpatterns = [
    path('', views.activity_logs, name='logs'),
    path('autocomplete/', views.autocomplete, name='autocomplete'),
]
