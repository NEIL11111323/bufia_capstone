from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from .forms import UserNotificationForm, MachineAlertForm, RiceMillSchedulingAlertForm, SendNotificationForm
from .models import UserNotification, MachineAlert, RiceMillSchedulingAlert
from django.contrib.auth import get_user_model

User = get_user_model()

# Create your views here.

def _is_admin(user):
    return user.is_superuser or user.is_staff

@login_required
def user_notifications(request):
    """View for regular users to see their notifications"""
    # Mark user's unread notifications as read
    if not _is_admin(request.user):
        UserNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    
    # Get user's notifications
    unread_list = UserNotification.objects.filter(user=request.user, is_read=False).order_by('-timestamp')
    read_list = UserNotification.objects.filter(user=request.user, is_read=True).order_by('-timestamp')[:50]

    return render(
        request,
        'notifications/user_notifications.html',
        {
            'unread_notifications': unread_list,
            'read_notifications': read_list,
        },
    )

@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_president())
def sent_notifications(request):
    """View for admins to see all notifications they have sent to users"""
    from django.db.models import Q, Count
    from datetime import datetime, timedelta
    
    # Get filter parameters
    category = request.GET.get('category', '')
    date_range = request.GET.get('date_range', '')
    sort_by = request.GET.get('sort', '-timestamp')
    search_query = request.GET.get('search', '')
    
    # Get all manually sent notifications (general, reminder, alert, etc.)
    # Exclude auto-generated notifications from signals (rental, appointment, irrigation)
    notifications = UserNotification.objects.exclude(
        Q(notification_type__icontains='rental') |
        Q(notification_type__icontains='appointment') |
        Q(notification_type__icontains='irrigation') |
        Q(notification_type__icontains='membership')
    )
    
    # Apply category filter
    if category:
        notifications = notifications.filter(notification_type=category)
    
    if date_range:
        today = datetime.now().date()
        if date_range == 'today':
            notifications = notifications.filter(timestamp__date=today)
        elif date_range == 'week':
            week_ago = today - timedelta(days=7)
            notifications = notifications.filter(timestamp__date__gte=week_ago)
        elif date_range == 'month':
            month_ago = today - timedelta(days=30)
            notifications = notifications.filter(timestamp__date__gte=month_ago)
    
    if search_query:
        notifications = notifications.filter(
            Q(message__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )
    
    # Apply sorting
    if sort_by:
        notifications = notifications.order_by(sort_by)
    
    # Get statistics
    total_sent = notifications.count()
    sent_today = notifications.filter(timestamp__date=datetime.now().date()).count()
    unique_recipients = notifications.values('user').distinct().count()
    
    # Get notification types for filter
    from .forms import SendNotificationForm
    notification_types = [choice[0] for choice in SendNotificationForm.NOTIFICATION_TYPES]
    
    # Get unread count for sidebar badge
    unread_count = UserNotification.objects.filter(is_read=False).count()
    
    # Paginate results
    from django.core.paginator import Paginator
    paginator = Paginator(notifications, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(
        request,
        'notifications/sent_notifications.html',
        {
            'page_obj': page_obj,
            'notification_types': notification_types,
            'total_sent': total_sent,
            'sent_today': sent_today,
            'unique_recipients': unique_recipients,
            'unread_count': unread_count,
            'current_filters': {
                'category': category,
                'date_range': date_range,
                'sort': sort_by,
                'search': search_query,
            }
        },
    )

@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_president())
def all_notifications(request):
    """Admin view for managing all notifications with filters and sorting"""
    from django.db.models import Q, Count
    from datetime import datetime, timedelta
    
    # Mark admin's unread notifications as read when they view this page
    UserNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    
    # Get filter parameters
    category = request.GET.get('category', '')
    recipient_group = request.GET.get('recipient', '')
    date_range = request.GET.get('date_range', '')
    read_status = request.GET.get('read_status', '')
    sort_by = request.GET.get('sort', '-timestamp')
    search_query = request.GET.get('search', '')
    
    # Start with all notifications
    notifications = UserNotification.objects.all()
    
    # Apply category filter
    if category:
        if category == 'rental':
            notifications = notifications.filter(notification_type__icontains='rental')
        elif category == 'appointment':
            notifications = notifications.filter(notification_type__icontains='appointment')
        elif category == 'irrigation':
            notifications = notifications.filter(notification_type__icontains='irrigation')
        elif category == 'membership':
            notifications = notifications.filter(notification_type__icontains='membership')
        elif category == 'general':
            # General notifications are those that don't contain rental, appointment, irrigation, or membership
            notifications = notifications.exclude(
                Q(notification_type__icontains='rental') |
                Q(notification_type__icontains='appointment') |
                Q(notification_type__icontains='irrigation') |
                Q(notification_type__icontains='membership')
            )
    
    if read_status == 'read':
        notifications = notifications.filter(is_read=True)
    elif read_status == 'unread':
        notifications = notifications.filter(is_read=False)
    
    if date_range:
        today = datetime.now().date()
        if date_range == 'today':
            notifications = notifications.filter(timestamp__date=today)
        elif date_range == 'week':
            week_ago = today - timedelta(days=7)
            notifications = notifications.filter(timestamp__date__gte=week_ago)
        elif date_range == 'month':
            month_ago = today - timedelta(days=30)
            notifications = notifications.filter(timestamp__date__gte=month_ago)
    
    if search_query:
        notifications = notifications.filter(
            Q(message__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )
    
    # Apply sorting
    if sort_by:
        notifications = notifications.order_by(sort_by)
    
    # Get statistics
    total_count = UserNotification.objects.count()
    unread_count = UserNotification.objects.filter(is_read=False).count()
    rental_count = UserNotification.objects.filter(notification_type__icontains='rental').count()
    appointment_count = UserNotification.objects.filter(notification_type__icontains='appointment').count()
    irrigation_count = UserNotification.objects.filter(notification_type__icontains='irrigation').count()
    membership_count = UserNotification.objects.filter(notification_type__icontains='membership').count()
    
    # Get notification types for filter dropdown - only show manual notification types
    from .forms import SendNotificationForm
    notification_types = [choice[0] for choice in SendNotificationForm.NOTIFICATION_TYPES]
    
    # Paginate results
    from django.core.paginator import Paginator
    paginator = Paginator(notifications, 50)  # 50 notifications per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(
        request,
        'notifications/all_notifications.html',
        {
            'page_obj': page_obj,
            'notification_types': notification_types,
            'total_count': total_count,
            'unread_count': unread_count,
            'rental_count': rental_count,
            'appointment_count': appointment_count,
            'irrigation_count': irrigation_count,
            'membership_count': membership_count,
            'current_filters': {
                'category': category,
                'recipient': recipient_group,
                'date_range': date_range,
                'read_status': read_status,
                'sort': sort_by,
                'search': search_query,
            }
        },
    )

@login_required
def machine_alerts(request):
    if request.method == 'POST':
        form = MachineAlertForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('notifications:machine_alerts')
    else:
        form = MachineAlertForm()
    alerts = MachineAlert.objects.all()
    return render(request, 'notifications/machine_alerts.html', {'form': form, 'alerts': alerts})

@login_required
def rice_mill_scheduling_alerts(request):
    if request.method == 'POST':
        form = RiceMillSchedulingAlertForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('notifications:rice_mill_scheduling_alerts')
    else:
        form = RiceMillSchedulingAlertForm()
    alerts = RiceMillSchedulingAlert.objects.all()
    return render(request, 'notifications/rice_mill_scheduling_alerts.html', {'form': form, 'alerts': alerts})

@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_president())
def send_notification(request):
    """View for admins to send notifications to users"""
    if request.method == 'POST':
        form = SendNotificationForm(request.POST)
        if form.is_valid():
            recipient_type = form.cleaned_data['recipient_type']
            notification_type = form.cleaned_data['notification_type']
            message = form.cleaned_data['message']
            specific_users_ids = form.cleaned_data.get('specific_users')
            
            # Determine recipients based on selection
            recipients = []
            if recipient_type == 'all':
                recipients = User.objects.all()
                recipient_count = recipients.count()
            elif recipient_type == 'members':
                recipients = User.objects.filter(is_verified=True)
                recipient_count = recipients.count()
            elif recipient_type == 'pending':
                recipients = User.objects.filter(membership_form_submitted=True, is_verified=False)
                recipient_count = recipients.count()
            elif recipient_type == 'specific' and specific_users_ids:
                # Parse comma-separated user IDs
                user_ids = [int(uid.strip()) for uid in specific_users_ids.split(',') if uid.strip()]
                recipients = User.objects.filter(id__in=user_ids)
                recipient_count = recipients.count()
            
            # Create notifications for all recipients
            notifications_created = 0
            for user in recipients:
                UserNotification.objects.create(
                    user=user,
                    notification_type=notification_type,
                    message=message
                )
                notifications_created += 1
            
            messages.success(
                request,
                f'Successfully sent notification to {notifications_created} user(s)!'
            )
            return redirect('notifications:send_notification')
    else:
        form = SendNotificationForm()
    
    # Get recent sent notifications for reference
    recent_notifications = UserNotification.objects.all().order_by('-timestamp')[:10]
    
    # Get unread count for sidebar badge
    unread_count = UserNotification.objects.filter(is_read=False).count()
    
    return render(request, 'notifications/send_notification.html', {
        'form': form,
        'recent_notifications': recent_notifications,
        'unread_count': unread_count
    })

@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_president())
def user_autocomplete(request):
    """API endpoint for user autocomplete search"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'users': []})
    
    # Search users by first name, last name, or username
    users = User.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(username__icontains=query)
    ).values('id', 'first_name', 'last_name', 'username')[:10]
    
    # Format results
    results = []
    for user in users:
        full_name = f"{user['first_name']} {user['last_name']}".strip()
        if not full_name:
            full_name = user['username']
        
        results.append({
            'id': user['id'],
            'name': full_name,
            'username': user['username']
        })
    
    return JsonResponse({'users': results})

@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_president())
def mark_admin_notifications_read(request):
    """Mark all admin's notifications as read when they open the dropdown"""
    if request.method == 'POST':
        UserNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_president())
def notification_detail(request, notification_id):
    """View notification details - shows requestor information only, no approval"""
    try:
        notification = UserNotification.objects.get(id=notification_id)
        
        # Mark as read
        if not notification.is_read:
            notification.is_read = True
            notification.save()
        
        # Get related rental if it exists
        rental = None
        if notification.related_object_id and 'rental' in notification.notification_type.lower():
            from machines.models import Rental
            try:
                rental = Rental.objects.select_related('machine', 'user').get(id=notification.related_object_id)
            except Rental.DoesNotExist:
                pass
        
        return render(request, 'notifications/notification_detail.html', {
            'notification': notification,
            'rental': rental,
        })
    except UserNotification.DoesNotExist:
        messages.error(request, 'Notification not found.')
        return redirect('notifications:all_notifications')

@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_president())
def delete_notification(request, notification_id):
    """Delete a notification"""
    if request.method == 'POST':
        try:
            notification = UserNotification.objects.get(id=notification_id)
            notification.delete()
            return JsonResponse({'success': True})
        except UserNotification.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Notification not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def notification_redirect(request, notification_id):
    """Handle notification click and redirect to appropriate page"""
    try:
        notification = UserNotification.objects.get(id=notification_id, user=request.user)
        
        # Mark as read
        if not notification.is_read:
            notification.is_read = True
            notification.save()
        
        # Get redirect URL
        redirect_url = notification.get_redirect_url()
        
        # If no specific redirect URL (general announcements), redirect based on user role
        if redirect_url is None:
            # Admins go to all notifications page, regular users go to their notifications
            if request.user.is_superuser or request.user.is_president():
                return redirect('notifications:all_notifications')
            else:
                return redirect('notifications:user_notifications')
        
        return redirect(redirect_url)
    except UserNotification.DoesNotExist:
        messages.error(request, 'Notification not found.')
        # Redirect based on user role
        if request.user.is_superuser or request.user.is_president():
            return redirect('notifications:all_notifications')
        else:
            return redirect('notifications:user_notifications')
