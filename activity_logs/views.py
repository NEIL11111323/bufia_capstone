from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.http import JsonResponse

def is_superuser(user):
    return user.is_superuser

@login_required
@user_passes_test(is_superuser)
def activity_logs(request):
    """Display system activity logs and audit trail"""
    
    # Get filter parameters
    action_filter = request.GET.get('action', 'all')
    search_query = request.GET.get('search', '')
    
    # Get all log entries
    logs = LogEntry.objects.select_related('user', 'content_type').order_by('-action_time')
    
    # Apply filters
    if action_filter == 'add':
        logs = logs.filter(action_flag=1)
    elif action_filter == 'change':
        logs = logs.filter(action_flag=2)
    elif action_filter == 'delete':
        logs = logs.filter(action_flag=3)
    
    # Apply search
    if search_query:
        logs = logs.filter(
            Q(user__username__icontains=search_query) |
            Q(object_repr__icontains=search_query) |
            Q(change_message__icontains=search_query)
        )
    
    # Limit to recent 100 entries for performance
    logs = logs[:100]
    
    # Get suggestions for autocomplete
    all_logs = LogEntry.objects.select_related('user', 'content_type').order_by('-action_time')[:200]
    users = set()
    objects = set()
    content_types = set()
    
    for log in all_logs:
        if log.user:
            users.add(log.user.get_full_name() or log.user.username)
        if log.object_repr:
            objects.add(log.object_repr)
        if log.content_type:
            content_types.add(str(log.content_type).title())
    
    # Add common search terms
    common_terms = ['Machine', 'Rental', 'User', 'Appointment', 'Payment', 'Notification']
    
    suggestions = list(users) + list(objects) + list(content_types) + common_terms
    
    context = {
        'logs': logs,
        'action_filter': action_filter,
        'search_query': search_query,
        'suggestions': suggestions[:50],  # Limit to 50 suggestions
    }
    
    return render(request, 'activity_logs/logs.html', context)

@login_required
@user_passes_test(is_superuser)
def autocomplete(request):
    """API endpoint for search autocomplete"""
    query = request.GET.get('q', '')
    
    if len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    logs = LogEntry.objects.select_related('user', 'content_type').order_by('-action_time')[:200]
    
    suggestions = set()
    
    for log in logs:
        # Add matching usernames
        if log.user:
            full_name = log.user.get_full_name() or log.user.username
            if query.lower() in full_name.lower():
                suggestions.add(full_name)
        
        # Add matching object names
        if log.object_repr and query.lower() in log.object_repr.lower():
            suggestions.add(log.object_repr)
        
        # Add matching content types
        if log.content_type and query.lower() in str(log.content_type).lower():
            suggestions.add(str(log.content_type).title())
    
    return JsonResponse({
        'suggestions': sorted(list(suggestions))[:20]
    })
