"""
Operator-specific notification views
"""
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.db.models import Q

from django.contrib.auth import get_user_model

from notifications.models import UserNotification
from notifications.operator_notifications import (
    get_operator_notification_count,
    mark_operator_notifications_read,
    get_operator_recent_notifications,
)


User = get_user_model()


def _is_operator_user(user):
    """Check if user has operator role"""
    return user.is_authenticated and user.role == User.OPERATOR


@login_required
def operator_notifications(request):
    """Enhanced operator notifications view with filtering"""
    if not _is_operator_user(request.user):
        return redirect('dashboard')
    
    # Handle mark all read
    if request.GET.get('mark_all_read'):
        mark_operator_notifications_read(request.user)
        return redirect('machines:operator_notifications')
    
    # Handle mark single read
    if request.GET.get('mark_read'):
        try:
            notification_id = int(request.GET.get('mark_read'))
            mark_operator_notifications_read(request.user, [notification_id])
        except (ValueError, TypeError):
            pass
        return redirect('machines:operator_notifications')
    
    # Get notifications with filtering
    notifications = UserNotification.objects.filter(user=request.user)
    
    # Apply filters
    filter_type = request.GET.get('filter')
    if filter_type == 'unread':
        notifications = notifications.filter(is_read=False)
    elif filter_type == 'job_assigned':
        notifications = notifications.filter(
            notification_type__in=[
                'operator_job_assigned',
                'operator_job_updated',
                'operator_schedule_change'
            ]
        )
    elif filter_type == 'harvest':
        notifications = notifications.filter(
            notification_type__in=[
                'operator_harvest_approved',
                'operator_harvest_rejected',
                'operator_payment_processed'
            ]
        )
    elif filter_type == 'urgent':
        notifications = notifications.filter(
            Q(notification_type__contains='urgent') |
            Q(notification_type='operator_urgent_job')
        )
    
    # Order by timestamp
    notifications = notifications.order_by('-timestamp')
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get unread count
    unread_count = get_operator_notification_count(request.user)
    
    context = {
        'notifications': page_obj,
        'unread_count': unread_count,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
        'current_filter': filter_type,
    }
    
    return render(request, 'machines/operator/notifications.html', context)


@login_required
def operator_notification_detail(request, notification_id):
    """View individual notification and mark as read"""
    if not _is_operator_user(request.user):
        return redirect('dashboard')
    
    try:
        notification = UserNotification.objects.get(
            id=notification_id,
            user=request.user
        )
        
        # Mark as read
        if not notification.is_read:
            notification.is_read = True
            notification.save()
        
        # Redirect to action URL if available
        if notification.action_url:
            return redirect(notification.action_url)

        redirect_url = notification.get_redirect_url()
        if redirect_url:
            return redirect(redirect_url)

        return redirect('machines:operator_notifications')
            
    except UserNotification.DoesNotExist:
        return redirect('machines:operator_notifications')


@login_required
def operator_notification_summary(request):
    """Get notification summary for dashboard widget"""
    if not _is_operator_user(request.user):
        return redirect('dashboard')
    
    # Get recent notifications (last 5)
    recent_notifications = get_operator_recent_notifications(request.user, limit=5)
    unread_count = get_operator_notification_count(request.user)
    
    # Categorize notifications
    job_notifications = recent_notifications.filter(
        notification_type__in=[
            'operator_job_assigned',
            'operator_job_updated',
            'operator_urgent_job'
        ]
    )[:3]
    
    harvest_notifications = recent_notifications.filter(
        notification_type__in=[
            'operator_harvest_approved',
            'operator_harvest_rejected'
        ]
    )[:2]
    
    context = {
        'recent_notifications': recent_notifications,
        'job_notifications': job_notifications,
        'harvest_notifications': harvest_notifications,
        'unread_count': unread_count,
    }
    
    return render(request, 'machines/operator/notification_summary_widget.html', context)
