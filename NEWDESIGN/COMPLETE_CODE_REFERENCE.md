# NORSU Campus Portal - Complete Code Reference

## 1. DJANGO SETTINGS (config/settings.py)

```python
"""
Django settings for config project.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-change-this-in-production'
DEBUG = True
ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'core',
    'academics',
    'news',
    'events',
    'contact',
    'dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'dashboard.context_processors.site_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'dashboard:index'
LOGOUT_REDIRECT_URL = 'home'
```

---

## 2. MAIN URL CONFIGURATION (config/urls.py)

```python
from django.contrib import admin
from django.urls import path, include, re_path
from accounts import views as accounts_views
from core import views as core_views
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('profile/', accounts_views.profile, name='profile'),
    path('settings/', accounts_views.settings_view, name='settings'),
    path('academics/', include('academics.urls')),
    path('news/', include('news.urls')),
    path('events/', include('events.urls')),
    path('contact/', include('contact.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('subscribe/', core_views.subscribe, name='subscribe'),
    re_path(r'^faculty/.*$', RedirectView.as_view(pattern_name='core:organization', permanent=False)),
    re_path(r'^staff/.*$', RedirectView.as_view(pattern_name='core:organization', permanent=False)),
]
```

---

## 3. ACCOUNTS APP

### accounts/models.py

```python
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('staff', 'Staff'),
        ('student', 'Student'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    phone = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=100, blank=True)
    id_number = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.role}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'userprofile'):
        instance.userprofile.save()
```

### accounts/forms.py

```python
from django import forms
from .models import UserProfile

class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['phone', 'department', 'id_number']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+63'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'id_number': forms.TextInput(attrs={'class': 'form-control'}),
        }
```

### accounts/forms_settings.py

```python
from django import forms
from django.contrib.auth.models import User

class SettingsForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField()
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
    
    def save(self):
        if self.user:
            self.user.first_name = self.cleaned_data['first_name']
            self.user.last_name = self.cleaned_data['last_name']
            self.user.email = self.cleaned_data['email']
            self.user.save()
```

### accounts/views.py

```python
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import ProfileForm
from .forms_settings import SettingsForm

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            if user.is_staff or user.is_superuser:
                return redirect('dashboard:index')
            return redirect('core:home')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'accounts/login.html')

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        id_number = request.POST.get('id_number', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        if not username or not password1 or not id_number:
            messages.error(request, 'Username, ID Number, and password are required.')
        elif password1 != password2:
            messages.error(request, 'Passwords do not match.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username is already taken.')
        else:
            user = User.objects.create_user(username=username, email=email, password=password1)
            user.save()
            profile = getattr(user, 'userprofile', None)
            if profile:
                profile.id_number = id_number
                profile.save()
            login(request, user)
            messages.success(request, 'Account created and logged in.')
            return redirect('accounts:profile')

    return render(request, 'accounts/register.html')

@login_required
def logout_view(request):
    logout(request)
    return redirect('core:home')

@login_required
def profile(request):
    profile = getattr(request.user, 'userprofile', None)

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProfileForm(instance=profile)

    context = {
        'user_obj': request.user,
        'profile': profile,
        'form': form,
    }
    return render(request, 'accounts/profile.html', context)

@login_required
def settings_view(request):
    if request.method == 'POST':
        form = SettingsForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Settings updated.')
            return redirect('accounts:settings')
        else:
            messages.error(request, 'Please correct the errors.')
    else:
        form = SettingsForm(user=request.user)

    context = {
        'user_obj': request.user,
        'form': form,
    }
    return render(request, 'accounts/settings.html', context)
```

### accounts/urls.py

```python
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('settings/', views.settings_view, name='settings'),
    path('password_change/', auth_views.PasswordChangeView.as_view(
        template_name='accounts/password_change.html',
        success_url='/accounts/password_change/done/'
    ), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='accounts/password_change_done.html'
    ), name='password_change_done'),
]
```

### accounts/admin.py

```python
from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'department', 'phone', 'created_at')
    list_filter = ('role', 'department')
    search_fields = ('user__username', 'id_number')
    readonly_fields = ('created_at',)
```

---

## 4. CORE APP

### core/models.py

```python
from django.db import models

# Core app has minimal models - mostly view-based
# Can extend with service/organization models as needed
```

### core/views.py

```python
from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

def home(request):
    latest_news = []
    upcoming_events = []
    
    try:
        from news.models import NewsPost
        latest_news = NewsPost.objects.filter(
            is_published=True
        ).order_by('-published_date')[:5]
    except:
        pass
    
    try:
        from events.models import Event
        upcoming_events = Event.objects.filter(
            date__gte=timezone.now()
        ).order_by('date')[:5]
    except:
        pass
    
    context = {
        'latest_news': latest_news,
        'upcoming_events': upcoming_events,
    }
    return render(request, 'core/home.html', context)

def about(request):
    return render(request, 'core/about.html')

def organization(request):
    context = {
        'faculty_highlights': [],
        'staff_highlights': [],
        'faculty_count': 0,
        'staff_count': 0,
    }
    return render(request, 'core/organization.html', context)

def services(request):
    services_list = [
        {'slug': 'registrar', 'name': 'Registrar', 'icon': 'fa-file-alt'},
        {'slug': 'library', 'name': 'Library', 'icon': 'fa-book-open'},
        {'slug': 'medical-dental', 'name': 'Medical and Dental', 'icon': 'fa-briefcase-medical'},
        {'slug': 'care-center', 'name': 'CARE Center', 'icon': 'fa-hands-helping'},
        {'slug': 'student-affairs', 'name': 'Student Affairs', 'icon': 'fa-users'},
    ]
    return render(request, 'core/services.html', {'services': services_list})

def service_detail(request, slug):
    services_map = {
        'registrar': {'title': 'Registrar', 'template': 'core/services/registrar.html'},
        'library': {'title': 'Library', 'template': 'core/services/library.html'},
        'medical-dental': {'title': 'Medical and Dental', 'template': 'core/services/medical_dental.html'},
        'care-center': {'title': 'CARE Center', 'template': 'core/services/care_center.html'},
        'student-affairs': {'title': 'Student Affairs', 'template': 'core/services/student_affairs.html'},
    }
    svc = services_map.get(slug)
    if not svc:
        return redirect('core:services')
    return render(request, svc['template'], {'title': svc['title']})

def admissions(request):
    context = {
        'contact_email': 'admissions@norsu-bayawan.edu.ph',
        'phone': '+63 XXX-XXXX-XXX',
        'address': 'Santa Catalina, Negros Oriental, Philippines',
    }
    return render(request, 'core/admissions.html', context)

def subscribe(request):
    if request.method != 'POST':
        return redirect('core:home')

    email = request.POST.get('email', '').strip()
    if not email:
        messages.error(request, 'Please provide an email address.')
        return redirect(request.META.get('HTTP_REFERER', 'core:home'))

    try:
        validate_email(email)
    except ValidationError:
        messages.error(request, 'Please provide a valid email address.')
        return redirect(request.META.get('HTTP_REFERER', 'core:home'))

    try:
        with open('subscriptions.txt', 'a', encoding='utf-8') as f:
            f.write(email + '\n')
    except:
        pass

    messages.success(request, 'Thanks — you have been subscribed to our newsletter.')
    return redirect(request.META.get('HTTP_REFERER', 'core:home'))

def privacy(request):
    return render(request, 'core/privacy.html')
```

### core/urls.py

```python
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('organization/', views.organization, name='organization'),
    path('services/', views.services, name='services'),
    path('services/<slug:slug>/', views.service_detail, name='service_detail'),
    path('admissions/', views.admissions, name='admissions'),
    path('privacy/', views.privacy, name='privacy'),
]
```

### core/admin.py

```python
from django.contrib import admin

# Core app admin configuration
```

---

## 5. ACADEMICS APP

### academics/models.py

```python
from django.db import models

class Department(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    head = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Course(models.Model):
    title = models.CharField(max_length=200)
    code = models.CharField(max_length=20)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    description = models.TextField()
    duration = models.CharField(max_length=50, help_text="e.g., 4 years")
    requirements = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.code} - {self.title}"
```

### academics/views.py

```python
from django.shortcuts import render, get_object_or_404
from .models import Department, Course

def department_list(request):
    departments = Department.objects.all()
    return render(request, 'academics/department_list.html', {'departments': departments})

def department_detail(request, pk):
    department = get_object_or_404(Department, pk=pk)
    courses = Course.objects.filter(department=department)
    return render(request, 'academics/department_detail.html', {
        'department': department,
        'courses': courses
    })

def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    return render(request, 'academics/course_detail.html', {'course': course})

def school_calendar(request):
    calendar_items = [
        {"title": "Spring Registration Opens", "date": "Jan 8, 2026", "category": "Registration"},
        {"title": "Start of Classes", "date": "Feb 5, 2026", "category": "Instruction"},
        {"title": "Midterm Exams", "date": "Mar 25-29, 2026", "category": "Exams"},
        {"title": "Holiday Break", "date": "Apr 9-12, 2026", "category": "Holiday"},
        {"title": "Final Exams", "date": "May 20-27, 2026", "category": "Exams"},
        {"title": "Grades Posting Deadline", "date": "Jun 3, 2026", "category": "Grades"},
    ]
    return render(request, 'academics/calendar.html', {"calendar_items": calendar_items})
```

### academics/urls.py

```python
from django.urls import path
from . import views

app_name = 'academics'

urlpatterns = [
    path('', views.department_list, name='index'),
    path('departments/', views.department_list, name='departments'),
    path('departments/<int:pk>/', views.department_detail, name='department_detail'),
    path('courses/<int:pk>/', views.course_detail, name='course_detail'),
    path('calendar/', views.school_calendar, name='calendar'),
]
```

### academics/admin.py

```python
from django.contrib import admin
from .models import Department, Course

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'head', 'email', 'phone')
    search_fields = ('name', 'head')

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'department', 'duration')
    list_filter = ('department',)
    search_fields = ('code', 'title')
```

---

## 6. DASHBOARD APP

### dashboard/models.py

```python
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.urls import reverse

class Course(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    outline = models.TextField(blank=True)
    schedule = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            slug = base
            counter = 1
            while Course.objects.filter(slug=slug).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('dashboard:student_course_detail', kwargs={'slug': self.slug})

class Enrollment(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'course')

    def __str__(self):
        return f"{self.student} in {self.course}"

class Assignment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.course})"

class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"Submission by {self.student} for {self.assignment}"

class Grade(models.Model):
    submission = models.OneToOneField(Submission, on_delete=models.CASCADE, related_name='grade')
    value = models.CharField(max_length=20)
    feedback = models.TextField(blank=True)
    graded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.value} for {self.submission}"

class Ticket(models.Model):
    STATUS_CHOICES = [('open', 'Open'), ('in_progress', 'In Progress'), ('closed', 'Closed')]
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='tickets')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')

    def __str__(self):
        return f"Ticket: {self.title} ({self.status})"

class Announcement(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    publish = models.BooleanField(default=True)

    def __str__(self):
        return self.title

class Document(models.Model):
    title = models.CharField(max_length=200)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class StaffTask(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='assigned_tasks')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_tasks')
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(null=True, blank=True)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return f"Task: {self.title} ({'done' if self.completed else 'open'})"

class StaffNote(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class ActivityLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.timestamp}: {self.user} - {self.action}"

class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification to {self.recipient}: {self.message[:40]}"

class SiteSetting(models.Model):
    site_name = models.CharField(max_length=100, default="Campus Portal")
    contact_email = models.EmailField(default="info@campus.edu")
    contact_phone = models.CharField(max_length=20, default="+63 XXX-XXXX-XXX")
    address = models.TextField(default="Campus Address")
    facebook_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Site Settings"

    def save(self, *args, **kwargs):
        if not self.pk and SiteSetting.objects.exists():
            existing = SiteSetting.objects.first()
            existing.site_name = self.site_name
            existing.contact_email = self.contact_email
            existing.contact_phone = self.contact_phone
            existing.address = self.address
            existing.facebook_url = self.facebook_url
            existing.twitter_url = self.twitter_url
            existing.instagram_url = self.instagram_url
            return existing.save(*args, **kwargs)
        return super().save(*args, **kwargs)
```

### dashboard/forms.py

```python
from django import forms
from .models import Course, Assignment, Submission, Grade, Ticket, Announcement, Document, StaffTask, StaffNote
from django.contrib.auth.models import User

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'outline', 'schedule']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'outline': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'schedule': forms.TextInput(attrs={'class': 'form-control'}),
        }

class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['title', 'description', 'due_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'due_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
        }

class GradeForm(forms.ModelForm):
    class Meta:
        model = Grade
        fields = ['value', 'feedback']
        widgets = {
            'value': forms.TextInput(attrs={'class': 'form-control'}),
            'feedback': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'body', 'publish']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
            'publish': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['title']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
        }

class StaffTaskForm(forms.ModelForm):
    class Meta:
        model = StaffTask
        fields = ['title', 'description', 'assigned_to', 'due_date', 'completed']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'assigned_to': forms.Select(attrs={'class': 'form-control'}),
            'due_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class StaffNoteForm(forms.ModelForm):
    class Meta:
        model = StaffNote
        fields = ['title', 'body']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }

class StudentEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
```

### dashboard/views.py

```python
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from .models import Course, Enrollment, Assignment, Submission, Grade, Ticket, Announcement, Document, StaffTask, StaffNote
from .forms import CourseForm, AssignmentForm, SubmissionForm, GradeForm, TicketForm, AnnouncementForm, DocumentUploadForm, StaffTaskForm, StaffNoteForm, StudentEditForm
from django.contrib.auth import get_user_model

User = get_user_model()

# Dashboard Index
@login_required
def dashboard_index(request):
    if not request.user.is_staff and not request.user.is_superuser:
        return redirect('dashboard:student_index')
    context = {'recentnews': [], 'recent_messages': []}
    return render(request, 'dashboard/index.html', context)

# ========== STUDENT VIEWS ==========

@login_required
def student_index(request):
    return render(request, 'dashboard/student/index.html')

@login_required
def student_courses(request):
    enrolled = Enrollment.objects.filter(student=request.user).values_list('course_id', flat=True)
    enrolled_courses = Course.objects.filter(id__in=enrolled)
    available = Course.objects.exclude(id__in=enrolled)
    return render(request, 'dashboard/student/courses.html', {
        'enrolled': enrolled_courses,
        'available': available
    })

@login_required
def student_course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug)
    is_enrolled = Enrollment.objects.filter(course=course, student=request.user).exists()
    assignments = course.assignments.all()
    
    total = assignments.count()
    submitted = Submission.objects.filter(assignment__in=assignments, student=request.user).count()
    progress = int((submitted / total) * 100) if total > 0 else 0

    return render(request, 'dashboard/student/course_detail.html', {
        'course': course,
        'is_enrolled': is_enrolled,
        'assignments': assignments,
        'progress': progress,
    })

@login_required
def student_join_course(request, slug):
    course = get_object_or_404(Course, slug=slug)
    Enrollment.objects.get_or_create(student=request.user, course=course)
    messages.success(request, f'You have joined {course.title}.')
    return redirect(course.get_absolute_url())

@login_required
def student_leave_course(request, slug):
    course = get_object_or_404(Course, slug=slug)
    Enrollment.objects.filter(student=request.user, course=course).delete()
    messages.success(request, f'You have left {course.title}.')
    return redirect('dashboard:student_courses')

@login_required
def assignment_detail(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
    submissions = Submission.objects.filter(assignment=assignment, student=request.user)
    return render(request, 'dashboard/student/assignment_detail.html', {
        'assignment': assignment,
        'submissions': submissions
    })

@login_required
def submit_assignment(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
    if request.method == 'POST':
        form = SubmissionForm(request.POST)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.assignment = assignment
            submission.student = request.user
            submission.save()
            messages.success(request, 'Assignment submitted successfully.')
            return redirect('dashboard:student_course_detail', slug=assignment.course.slug)
    else:
        form = SubmissionForm()
    return render(request, 'dashboard/student/submit_assignment.html', {
        'form': form,
        'assignment': assignment
    })

@login_required
def student_assignments(request):
    enrollments = Enrollment.objects.filter(student=request.user).values_list('course_id', flat=True)
    assignments = Assignment.objects.filter(course_id__in=enrollments)
    return render(request, 'dashboard/student/assignments.html', {'assignments': assignments})

@login_required
def student_grades(request):
    submissions = Submission.objects.filter(student=request.user).select_related('grade')
    return render(request, 'dashboard/student/grades.html', {'submissions': submissions})

# ========== FACULTY VIEWS ==========

@login_required
def faculty_index(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard:student_index')
    return render(request, 'dashboard/faculty/index.html')

@login_required
def faculty_courses_list(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard:index')
    courses = Course.objects.all().order_by('title')
    return render(request, 'dashboard/faculty/courses_list.html', {'courses': courses})

@login_required
def faculty_course_create(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard:index')
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course created.')
            return redirect('dashboard:faculty_courses_list')
    else:
        form = CourseForm()
    return render(request, 'dashboard/faculty/course_form.html', {'form': form})

@login_required
def faculty_course_edit(request, slug):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard:index')
    course = get_object_or_404(Course, slug=slug)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course updated.')
            return redirect('dashboard:faculty_courses_list')
    else:
        form = CourseForm(instance=course)
    return render(request, 'dashboard/faculty/course_form.html', {'form': form, 'course': course})

@login_required
def faculty_course_materials(request, slug):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard:index')
    course = get_object_or_404(Course, slug=slug)
    assignments = course.assignments.all()
    if request.method == 'POST':
        form = AssignmentForm(request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.course = course
            assignment.save()
            messages.success(request, 'Material uploaded.')
            return redirect('dashboard:faculty_course_materials', slug=slug)
    else:
        form = AssignmentForm()
    return render(request, 'dashboard/faculty/course_materials.html', {
        'course': course,
        'assignments': assignments,
        'form': form
    })

@login_required
def faculty_grade_submissions_list(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard:index')
    submissions = Submission.objects.select_related('assignment', 'student').order_by('-submitted_at')
    return render(request, 'dashboard/faculty/grade_submissions_list.html', {'submissions': submissions})

@login_required
def faculty_grade_submission(request, submission_id):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard:index')
    submission = get_object_or_404(Submission, pk=submission_id)
    try:
        grade = submission.grade
    except Grade.DoesNotExist:
        grade = None
    
    if request.method == 'POST':
        form = GradeForm(request.POST, instance=grade)
        if form.is_valid():
            g = form.save(commit=False)
            g.submission = submission
            g.save()
            messages.success(request, 'Grade saved.')
            return redirect('dashboard:faculty_grade_submissions_list')
    else:
        form = GradeForm(instance=grade)
    return render(request, 'dashboard/faculty/grade_form.html', {'submission': submission, 'form': form})

@login_required
def faculty_staff_tasks(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard:index')
    tasks = StaffTask.objects.all().order_by('-created_at')
    if request.method == 'POST':
        form = StaffTaskForm(request.POST)
        if form.is_valid():
            t = form.save(commit=False)
            t.created_by = request.user
            t.save()
            messages.success(request, 'Task created.')
            return redirect('dashboard:faculty_staff_tasks')
    else:
        form = StaffTaskForm()
    return render(request, 'dashboard/faculty/staff_tasks.html', {'tasks': tasks, 'form': form})

@login_required
def faculty_staff_notes(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard:index')
    notes = StaffNote.objects.all().order_by('-created_at')
    if request.method == 'POST':
        form = StaffNoteForm(request.POST)
        if form.is_valid():
            n = form.save(commit=False)
            n.author = request.user
            n.save()
            messages.success(request, 'Note saved.')
            return redirect('dashboard:faculty_staff_notes')
    else:
        form = StaffNoteForm()
    return render(request, 'dashboard/faculty/staff_notes.html', {'notes': notes, 'form': form})

# ========== STAFF VIEWS ==========

@login_required
def staff_index(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard:student_index')
    return render(request, 'dashboard/staff/index.html')

@login_required
def staff_students_list(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard:index')
    students = User.objects.filter(is_staff=False).order_by('last_name', 'first_name')
    return render(request, 'dashboard/staff/students_list.html', {'students': students})

@login_required
def staff_edit_student(request, user_id):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard:index')
    student = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        form = StudentEditForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student profile updated.')
            return redirect('dashboard:staff_students_list')
    else:
        form = StudentEditForm(instance=student)
    return render(request, 'dashboard/staff/edit_student.html', {'form': form, 'student': student})

@login_required
@require_http_methods(['POST'])
def staff_reset_password(request, user_id):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard:index')
    student = get_object_or_404(User, pk=user_id)
    temp = User.objects.make_random_password()
    student.set_password(temp)
    student.save()
    messages.success(request, f"Password reset. Temporary: {temp}")
    return redirect('dashboard:staff_edit_student', user_id=user_id)

@login_required
def staff_enroll_student(request, user_id, slug):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard:index')
    student = get_object_or_404(User, pk=user_id)
    course = get_object_or_404(Course, slug=slug)
    Enrollment.objects.get_or_create(student=student, course=course)
    messages.success(request, f"{student.username} enrolled in {course.title}.")
    return redirect('dashboard:staff_students_list')

@login_required
def tickets_list(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard:index')
    tickets = Ticket.objects.all().order_by('-created_at')
    return render(request, 'dashboard/staff/tickets_list.html', {'tickets': tickets})

@login_required
def ticket_detail(request, pk):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard:index')
    ticket = get_object_or_404(Ticket, pk=pk)
    if request.method == 'POST':
        form = TicketForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ticket updated.')
            return redirect('dashboard:ticket_detail', pk=pk)
    else:
        form = TicketForm(instance=ticket)
    return render(request, 'dashboard/staff/ticket_detail.html', {'ticket': ticket, 'form': form})

@login_required
def announcements_list(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard:index')
    items = Announcement.objects.all().order_by('-created_at')
    return render(request, 'dashboard/staff/announcements_list.html', {'items': items})

@login_required
def announcement_create(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard:index')
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            ann = form.save(commit=False)
            ann.created_by = request.user
            ann.save()
            messages.success(request, 'Announcement published.')
            return redirect('dashboard:announcements_list')
    else:
        form = AnnouncementForm()
    return render(request, 'dashboard/staff/announcement_form.html', {'form': form})

@login_required
def documents_list(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard:index')
    docs = Document.objects.all().order_by('-uploaded_at')
    return render(request, 'dashboard/staff/documents_list.html', {'docs': docs})

@login_required
def document_upload(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard:index')
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST)
        if form.is_valid():
            d = form.save(commit=False)
            d.uploaded_by = request.user
            d.save()
            messages.success(request, 'Document uploaded.')
            return redirect('dashboard:documents_list')
    else:
        form = DocumentUploadForm()
    return render(request, 'dashboard/staff/document_upload.html', {'form': form})
```

### dashboard/urls.py

```python
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_index, name='index'),
    
    # Student
    path('student/', views.student_index, name='student_index'),
    path('student/courses/', views.student_courses, name='student_courses'),
    path('student/course/<slug:slug>/', views.student_course_detail, name='student_course_detail'),
    path('student/course/<slug:slug>/join/', views.student_join_course, name='student_join_course'),
    path('student/course/<slug:slug>/leave/', views.student_leave_course, name='student_leave_course'),
    path('student/assignment/<int:pk>/', views.assignment_detail, name='assignment_detail'),
    path('student/assignment/<int:pk>/submit/', views.submit_assignment, name='submit_assignment'),
    path('student/assignments/', views.student_assignments, name='student_assignments'),
    path('student/grades/', views.student_grades, name='student_grades'),
    
    # Faculty
    path('faculty/', views.faculty_index, name='faculty_index'),
    path('faculty/courses/', views.faculty_courses_list, name='faculty_courses_list'),
    path('faculty/courses/new/', views.faculty_course_create, name='faculty_course_create'),
    path('faculty/courses/<slug:slug>/edit/', views.faculty_course_edit, name='faculty_course_edit'),
    path('faculty/courses/<slug:slug>/materials/', views.faculty_course_materials, name='faculty_course_materials'),
    path('faculty/grade-submissions/list/', views.faculty_grade_submissions_list, name='faculty_grade_submissions_list'),
    path('faculty/grade-submissions/<int:submission_id>/grade/', views.faculty_grade_submission, name='faculty_grade_submission'),
    path('faculty/staff-tasks/', views.faculty_staff_tasks, name='faculty_staff_tasks'),
    path('faculty/staff-notes/', views.faculty_staff_notes, name='faculty_staff_notes'),
    
    # Staff
    path('staff/', views.staff_index, name='staff_index'),
    path('staff/students/list/', views.staff_students_list, name='staff_students_list'),
    path('staff/students/<int:user_id>/edit/', views.staff_edit_student, name='staff_edit_student'),
    path('staff/students/<int:user_id>/reset-password/', views.staff_reset_password, name='staff_reset_password'),
    path('staff/students/<int:user_id>/enroll/<slug:slug>/', views.staff_enroll_student, name='staff_enroll_student'),
    path('staff/support/tickets/', views.tickets_list, name='tickets_list'),
    path('staff/support/tickets/<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('staff/support/announcements/', views.announcements_list, name='announcements_list'),
    path('staff/support/announcements/new/', views.announcement_create, name='announcement_create'),
    path('staff/support/documents/', views.documents_list, name='documents_list'),
    path('staff/support/documents/upload/', views.document_upload, name='document_upload'),
]
```

### dashboard/admin.py

```python
from django.contrib import admin
from .models import (
    Course, Enrollment, Assignment, Submission, Grade,
    Ticket, Announcement, Document, StaffTask, StaffNote,
    ActivityLog, Notification, SiteSetting
)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('title',)}

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'joined_at')
    list_filter = ('course', 'joined_at')

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'due_date', 'created_at')
    list_filter = ('course', 'created_at')

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'assignment', 'submitted_at')
    list_filter = ('submitted_at',)

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('value', 'submission', 'graded_at')

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'created_at')

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'publish', 'created_by', 'created_at')
    list_filter = ('publish', 'created_at')

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'uploaded_by', 'uploaded_at')

@admin.register(StaffTask)
class StaffTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'assigned_to', 'completed', 'due_date')
    list_filter = ('completed', 'due_date')

@admin.register(StaffNote)
class StaffNoteAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'created_at')

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp')
    list_filter = ('timestamp',)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'message', 'read', 'created_at')
    list_filter = ('read', 'created_at')

@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'contact_email', 'updated_at')
```

### dashboard/context_processors.py

```python
from .models import SiteSetting

def site_settings(request):
    try:
        settings = SiteSetting.objects.first()
    except:
        settings = None
    return {'site_settings': settings}
```

---

## 7. NEWS APP

### news/models.py

```python
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse

class NewsPost(models.Model):
    CATEGORY_CHOICES = [
        ('announcement', 'Announcement'),
        ('academic', 'Academic'),
        ('research', 'Research'),
        ('sports', 'Sports'),
        ('event', 'Event'),
        ('general', 'General'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    excerpt = models.TextField(max_length=300)
    content = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    published_date = models.DateTimeField(default=timezone.now)
    is_published = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_date']
        verbose_name_plural = 'News Posts'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            original_slug = self.slug
            counter = 1
            while NewsPost.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f'{original_slug}-{counter}'
                counter += 1
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('news:detail', kwargs={'slug': self.slug})
```

### news/views.py

```python
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from .models import NewsPost

def news_list(request):
    news_list = NewsPost.objects.filter(is_published=True).order_by('-published_date')
    paginator = Paginator(news_list, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'news_posts': page_obj,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
    }
    return render(request, 'news/news_list.html', context)

def news_detail(request, slug):
    news = get_object_or_404(NewsPost, slug=slug, is_published=True)
    context = {
        'news': news,
        'news_post': news,
    }
    return render(request, 'news/news_detail.html', context)
```

### news/urls.py

```python
from django.urls import path
from . import views

app_name = 'news'

urlpatterns = [
    path('', views.news_list, name='list'),
    path('<slug:slug>/', views.news_detail, name='detail'),
]
```

### news/admin.py

```python
from django.contrib import admin
from .models import NewsPost

@admin.register(NewsPost)
class NewsPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author', 'is_published', 'published_date')
    list_filter = ('category', 'is_published', 'published_date')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at')
```

---

## 8. EVENTS APP

### events/models.py

```python
from django.db import models
from django.utils import timezone

class Event(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    content = models.TextField(blank=True)
    date = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Events"
        ordering = ['-date']

    def __str__(self):
        return self.title
```

### events/views.py

```python
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from .models import Event

def event_list(request):
    upcoming_events = Event.objects.filter(date__gte=timezone.now()).order_by('date')
    past_events = Event.objects.filter(date__lt=timezone.now()).order_by('-date')
    
    context = {
        'upcoming_events': upcoming_events,
        'past_events': past_events,
    }
    return render(request, 'events/event_list.html', context)

def event_detail(request, slug):
    event = get_object_or_404(Event, slug=slug)
    context = {'event': event}
    return render(request, 'events/event_detail.html', context)
```

### events/urls.py

```python
from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('', views.event_list, name='list'),
    path('<slug:slug>/', views.event_detail, name='detail'),
]
```

### events/admin.py

```python
from django.contrib import admin
from .models import Event

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'location', 'created_at')
    list_filter = ('date',)
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
```

---

## 9. CONTACT APP

### contact/models.py

```python
from django.db import models

class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.subject}"
```

### contact/forms.py

```python
from django import forms
from .models import ContactMessage

class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }
```

### contact/views.py

```python
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import ContactForm

def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thank you for your message!')
            return redirect('contact:contact')
    else:
        form = ContactForm()

    return render(request, 'contact/contact.html', {'form': form})
```

### contact/urls.py

```python
from django.urls import path
from . import views

app_name = 'contact'

urlpatterns = [
    path('', views.contact_view, name='contact'),
]
```

### contact/admin.py

```python
from django.contrib import admin
from .models import ContactMessage

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('name', 'email', 'subject')
    readonly_fields = ('created_at',)
```

---

## 10. REQUIREMENTS.txt

```
Django>=4.2,<5.0
```

---

**System Design Code Generated:** February 14, 2026  
**Framework:** Django 4.2.7  
**Ready to Deploy:** Development environment
