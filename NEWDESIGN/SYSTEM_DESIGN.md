# NORSU Campus Portal System - Design Architecture

## 1. PROJECT OVERVIEW

**Project Name:** NORSU Santa Catalina - Bayawan Campus Portal
**Technology Stack:** Django 4.2.7, Python, SQLite3
**Type:** Educational Portal / Learning Management System
**Core Purpose:** Multi-role educational platform (Students, Faculty, Staff)

---

## 2. DEPENDENCIES

```
Django>=4.2,<5.0
```

---

## 3. SYSTEM ARCHITECTURE

### Applications Structure
```
Project/
├── config/              # Django settings & URL routing
├── accounts/            # User authentication & profiles
├── academics/           # Academic programs & courses
├── core/                # Portal homepage & services
├── dashboard/           # LMS for students/faculty/staff
├── news/                # News & announcements
├── events/              # Events management
├── contact/             # Contact form handling
├── templates/           # HTML templates
├── static/              # CSS, JS, static files
└── db.sqlite3           # SQLite database
```

### Installed Apps
- `django.contrib.admin` - Admin interface
- `django.contrib.auth` - Authentication
- `django.contrib.contenttypes` - Content types
- `django.contrib.sessions` - Sessions
- `django.contrib.messages` - Messaging
- `django.contrib.staticfiles` - Static files
- `accounts` - User management
- `core` - Core features
- `academics` - Academics
- `news` - News system
- `events` - Events
- `contact` - Contact forms
- `dashboard` - LMS

---

## 4. DATABASE MODELS

### 4.1 ACCOUNTS APP - User Management

#### UserProfile
```python
Fields:
- user (OneToOneField -> User)
- role (CharField: 'admin', 'staff', 'student')
- phone (CharField)
- department (CharField)
- id_number (CharField)
- created_at (DateTimeField)

Purpose: Extends User model with profile data & role assignment
Signal: Auto-create on User creation
```

---

### 4.2 ACADEMICS APP - Academic Structure

#### Department
```python
Fields:
- name (CharField)
- description (TextField)
- head (CharField)
- email (EmailField)
- phone (CharField)
- created_at (DateTimeField)

Ordering: By name
Purpose: Organize academic structure
```

#### Course (Academics)
```python
Fields:
- title (CharField)
- code (CharField)
- department (ForeignKey -> Department)
- description (TextField)
- duration (CharField)
- requirements (TextField)
- created_at (DateTimeField)

Purpose: Define academic courses
```

---

### 4.3 DASHBOARD APP - Learning Management System

#### Course (Dashboard)
```python
Fields:
- title (CharField)
- slug (SlugField, unique)
- description (TextField)
- outline (TextField)
- schedule (CharField)
- created_at (DateTimeField)

Purpose: LMS courses (different from academics)
Auto: Generate slug from title
Method: get_absolute_url() for routing
```

#### Enrollment
```python
Fields:
- student (ForeignKey -> User)
- course (ForeignKey -> Course)
- joined_at (DateTimeField)

Constraint: unique_together (student, course)
Purpose: Track student-course relationships
```

#### Assignment
```python
Fields:
- course (ForeignKey -> Course, related_name='assignments')
- title (CharField)
- description (TextField)
- due_date (DateTimeField)
- created_at (DateTimeField)

Ordering: By -created_at (newest first)
Purpose: Course assignments/materials
```

#### Submission
```python
Fields:
- assignment (ForeignKey -> Assignment, related_name='submissions')
- student (ForeignKey -> User)
- text (TextField)
- submitted_at (DateTimeField)

Ordering: By -submitted_at
Purpose: Student assignment submissions
```

#### Grade
```python
Fields:
- submission (OneToOneField -> Submission, related_name='grade')
- value (CharField) - 'A', 'B+', '85', etc.
- feedback (TextField)
- graded_at (DateTimeField)

Purpose: Grade submissions with feedback
```

#### Ticket
```python
Fields:
- title (CharField)
- description (TextField)
- created_by (ForeignKey -> User)
- created_at (DateTimeField)
- status (CharField: 'open', 'in_progress', 'closed')

Purpose: Support ticket system
```

#### Announcement
```python
Fields:
- title (CharField)
- body (TextField)
- created_by (ForeignKey -> User)
- created_at (DateTimeField)
- publish (BooleanField)

Purpose: Campus-wide announcements
```

#### Document
```python
Fields:
- title (CharField)
- uploaded_by (ForeignKey -> User)
- uploaded_at (DateTimeField)

Purpose: Resource management
```

#### StaffTask
```python
Fields:
- title (CharField)
- description (TextField)
- assigned_to (ForeignKey -> User, related_name='assigned_tasks')
- created_by (ForeignKey -> User, related_name='created_tasks')
- created_at (DateTimeField)
- due_date (DateTimeField)
- completed (BooleanField)

Purpose: Internal task assignment
```

#### StaffNote
```python
Fields:
- title (CharField)
- body (TextField)
- author (ForeignKey -> User)
- created_at (DateTimeField)

Purpose: Internal notes
```

#### ActivityLog
```python
Fields:
- user (ForeignKey -> User)
- action (CharField)
- timestamp (DateTimeField)

Purpose: Audit trail
```

#### Notification
```python
Fields:
- recipient (ForeignKey -> User, related_name='notifications')
- message (CharField)
- created_at (DateTimeField)
- read (BooleanField)

Purpose: User notifications
```

#### SiteSetting
```python
Fields:
- site_name (CharField)
- contact_email (EmailField)
- contact_phone (CharField)
- address (TextField)
- facebook_url (URLField)
- twitter_url (URLField)
- instagram_url (URLField)
- updated_at (DateTimeField)

Pattern: Singleton (only one instance)
Purpose: Site-wide configuration
```

---

### 4.4 NEWS APP - News Management

#### NewsPost
```python
Fields:
- title (CharField)
- slug (SlugField, unique)
- excerpt (TextField)
- content (TextField)
- category (CharField: 'announcement', 'academic', 'research', 'sports', 'event', 'general')
- author (ForeignKey -> User)
- published_date (DateTimeField)
- is_published (BooleanField)
- is_featured (BooleanField)
- created_at (DateTimeField)
- updated_at (DateTimeField)

Auto: Generate slug from title
Purpose: News posts with categories
```

---

### 4.5 EVENTS APP - Event Management

#### Event
```python
Fields:
- title (CharField)
- slug (SlugField, unique)
- description (TextField)
- content (TextField)
- date (DateTimeField)
- location (CharField)
- created_at (DateTimeField)
- updated_at (DateTimeField)

Ordering: By -date (newest first)
Purpose: Campus events calendar
```

---

### 4.6 CONTACT APP - Contact Management

#### ContactMessage
```python
Fields:
- name (CharField)
- email (EmailField)
- subject (CharField)
- message (TextField)
- created_at (DateTimeField)
- is_read (BooleanField)

Ordering: By -created_at
Purpose: Store contact form submissions
```

---

## 5. URL ROUTING ARCHITECTURE

### Main URL Configuration (config/urls.py)
```
/admin/                     → Django admin
/                          → core.urls
/accounts/                 → accounts.urls
/profile/                  → accounts.profile
/settings/                 → accounts.settings
/academics/                → academics.urls
/news/                     → news.urls
/events/                   → events.urls
/contact/                  → contact.urls
/dashboard/                → dashboard.urls
/subscribe/                → core.subscribe
```

### Core URLs
```
GET  /                     → home (news + events)
GET  /about/              → about page
GET  /organization/       → faculty/staff directory
GET  /services/           → services list
GET  /services/<slug>/    → service detail
GET  /admissions/         → admissions info
GET  /privacy/            → privacy policy
POST /subscribe/          → newsletter subscription
```

### Authentication URLs (accounts/)
```
GET  /accounts/login/              → login form
POST /accounts/login/              → process login
GET  /accounts/register/           → register form
POST /accounts/register/           → process registration
GET  /accounts/logout/             → logout user
GET  /accounts/profile/            → view profile
POST /accounts/profile/            → update profile
GET  /accounts/settings/           → settings page
POST /accounts/settings/           → update settings
GET  /accounts/password_change/    → change password form
POST /accounts/password_change/    → process password change
```

### Academic URLs (academics/)
```
GET /academics/                    → department list
GET /academics/departments/        → department list
GET /academics/departments/<id>/   → department detail + courses
GET /academics/courses/<id>/       → course detail
GET /academics/calendar/           → academic calendar
```

### Dashboard URLs - Student Area
```
GET  /dashboard/student/                        → dashboard home
GET  /dashboard/student/courses/                → enrolled & available courses
GET  /dashboard/student/course/<slug>/          → course detail + materials
POST /dashboard/student/course/<slug>/join/     → enroll in course
POST /dashboard/student/course/<slug>/leave/    → unenroll from course
GET  /dashboard/student/assignment/<id>/       → assignment detail
GET  /dashboard/student/assignment/<id>/submit/→ submission form
POST /dashboard/student/assignment/<id>/submit/→ process submission
GET  /dashboard/student/assignments/           → list assignments
GET  /dashboard/student/grades/                → view grades
```

### Dashboard URLs - Faculty Area
```
GET  /dashboard/faculty/                       → faculty dashboard
GET  /dashboard/faculty/courses/               → course list
GET  /dashboard/faculty/courses/new/           → create course form
POST /dashboard/faculty/courses/new/           → process course creation
GET  /dashboard/faculty/courses/<slug>/edit/   → edit course form
POST /dashboard/faculty/courses/<slug>/edit/   → process course edit
GET  /dashboard/faculty/courses/<slug>/materials/ → manage materials
POST /dashboard/faculty/courses/<slug>/materials/ → upload assignment
GET  /dashboard/faculty/grade-submissions/list/ → student submissions
GET  /dashboard/faculty/grade-submissions/<id>/grade/ → grading form
POST /dashboard/faculty/grade-submissions/<id>/grade/ → submit grade
GET  /dashboard/faculty/staff-tasks/          → task management
POST /dashboard/faculty/staff-tasks/          → create task
GET  /dashboard/faculty/staff-notes/          → notes management
POST /dashboard/faculty/staff-notes/          → create note
```

### Dashboard URLs - Staff Area
```
GET  /dashboard/staff/                         → staff dashboard
GET  /dashboard/staff/students/list/           → student list
GET  /dashboard/staff/students/<id>/edit/      → edit student form
POST /dashboard/staff/students/<id>/edit/      → process student edit
POST /dashboard/staff/students/<id>/reset-password/ → reset password
GET  /dashboard/staff/students/<id>/performance/ → view student performance
POST /dashboard/staff/students/<id>/enroll/<slug>/   → enroll student
POST /dashboard/staff/students/<id>/unenroll/<slug>/ → unenroll student
GET  /dashboard/staff/support/tickets/        → ticket list
GET  /dashboard/staff/support/tickets/<id>/   → ticket detail
POST /dashboard/staff/support/tickets/<id>/   → update ticket
GET  /dashboard/staff/support/announcements/  → announcements list
GET  /dashboard/staff/support/announcements/new/ → create announcement
POST /dashboard/staff/support/announcements/new/ → process announcement
GET  /dashboard/staff/support/documents/      → documents list
GET  /dashboard/staff/support/documents/upload/ → upload form
POST /dashboard/staff/support/documents/upload/ → process upload
```

### News URLs
```
GET /news/              → news list (paginated)
GET /news/<slug>/       → news detail
```

### Events URLs
```
GET /events/            → event list (upcoming & past)
GET /events/<slug>/     → event detail
```

### Contact URLs
```
GET  /contact/          → contact form
POST /contact/          → process contact submission
```

---

## 6. VIEW LAYER ARCHITECTURE

### Core Views
**home(request)**
- Fetch latest 5 published news posts
- Fetch upcoming 5 events
- Context: {latest_news, upcoming_events}

**about(request)**
- Static about page

**organization(request)**
- Display faculty & staff members
- Try to import from faculty/staff apps
- Graceful fallback if unavailable

**services(request)**
- List available services

**admissions(request)**
- Admissions information

**subscribe(request)**
- POST: Validate email, save to text file
- Redirect to referrer with success message

---

### Account Views
**login_view(request)**
- GET: Display login form
- POST: Authenticate user
- Routes: staff → /dashboard/, others → /home

**register_view(request)**
- GET: Display registration form
- POST: Create user + auto-create UserProfile
- Validate: password match, unique username
- Login & redirect to profile

**profile(request)**
- GET: Display profile form
- POST: Update profile data
- Form: ProfileForm

**settings_view(request)**
- GET: Display settings form
- POST: Update settings
- Form: SettingsForm

**logout_view(request)**
- Logout user, redirect to home

---

### Academic Views
**department_list(request)**
- List all departments ordered by name

**department_detail(request, pk)**
- Show department + related courses

**course_detail(request, pk)**
- Show course information

**school_calendar(request)**
- Display academic calendar with key dates

---

### Dashboard Views - Student

**student_dashboard(request)**
- Student home dashboard

**student_courses(request)**
- Enrolled courses
- Available courses to enroll

**student_course_detail(request, slug)**
- Course materials & assignments
- Progress calculation: (submissions / total assignments) * 100
- Enrollment status check

**student_join_course(request, slug)**
- Create enrollment record

**student_leave_course(request, slug)**
- Delete enrollment record

**assignment_detail(request, pk)**
- Show assignment + student submissions

**submit_assignment(request, pk)**
- POST: Save submission (text/file)

**student_assignments(request)**
- List all assignments

**student_grades(request)**
- List all grades received

---

### Dashboard Views - Faculty

**faculty_courses_list(request)**
- List all courses for management

**faculty_course_create(request)**
- GET: Course creation form
- POST: Create course with auto-slug

**faculty_course_edit(request, slug)**
- GET: Edit form
- POST: Update course

**faculty_course_materials(request, slug)**
- Show assignments
- POST: Upload new assignment

**faculty_grade_submissions_list(request)**
- List all student submissions

**faculty_grade_submission(request, submission_id)**
- GET: Grading form
- POST: Save grade with feedback

**faculty_staff_tasks(request)**
- Manage task assignments

**faculty_staff_notes(request)**
- Manage internal notes

---

### Dashboard Views - Staff

**staff_students_list(request)**
- List all students

**staff_edit_student(request, user_id)**
- Edit student profile

**staff_reset_password(request, user_id)**
- Generate temporary password

**staff_enroll_student(request, user_id, slug)**
- Create enrollment

**staff_unenroll_student(request, user_id, slug)**
- Delete enrollment

**staff_view_performance(request, user_id)**
- Show student submissions & grades

**tickets_list(request)**
- List support tickets

**ticket_detail(request, pk)**
- View & update ticket status

**announcements_list(request)**
- List announcements

**announcement_create(request)**
- Create announcement

**documents_list(request)**
- List documents

**document_upload(request)**
- Upload document

---

### News Views
**news_list(request)**
- Paginated list (9 per page)
- Filter: is_published=True
- Order: -published_date

**news_detail(request, slug)**
- Display single news post

---

### Events Views
**event_list(request)**
- Upcoming events (date >= now)
- Past events (date < now)

**event_detail(request, slug)**
- Display single event

---

### Contact Views
**contact_view(request)**
- GET: Display contact form
- POST: Save ContactMessage

---

## 7. FORMS ARCHITECTURE

### Authentication Forms
```
ProfileForm:
- phone
- department
- id_number

SettingsForm:
- User settings & preferences
```

### Academic Forms
```
CourseForm:
- title
- slug
- description
- outline
- schedule
```

### Dashboard Forms
```
AssignmentForm:
- title
- description
- due_date

SubmissionForm:
- text (textarea)

GradeForm:
- value
- feedback

TicketForm:
- title
- description
- status

AnnouncementForm:
- title
- body
- publish

DocumentUploadForm:
- title

StaffTaskForm:
- title
- description
- assigned_to
- due_date
- completed

StaffNoteForm:
- title
- body

StudentEditForm:
- Edit student information
```

### Contact Forms
```
ContactForm:
- name
- email
- subject
- message
```

---

## 8. AUTHENTICATION & AUTHORIZATION

### User Roles
1. **Student** (default)
   - Access: Student dashboard
   - Can: Enroll in courses, submit assignments, view grades

2. **Staff** (is_staff=True)
   - Access: Staff management area
   - Can: Manage students, reset passwords, create tickets/announcements

3. **Admin** (is_superuser=True)
   - Access: Everything + Django admin
   - Can: All operations

### Protection Pattern
```python
@login_required
def view_name(request):
    # All dashboard views require login
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard:index')
    # Rest of view logic
```

### Login Flow
```
User → /accounts/login/ → authenticate() → 
if staff → /dashboard/ else → /
```

---

## 9. DJANGO SETTINGS CONFIGURATION

### Key Settings
```python
# Security
SECRET_KEY = '...'  # Change in production
DEBUG = True        # Set False in production
ALLOWED_HOSTS = []  # Set in production

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Static Files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Templates
TEMPLATES = [{
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
}]

# Login URLs
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'dashboard:index'
LOGOUT_REDIRECT_URL = 'home'

# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

---

## 10. CONTEXT PROCESSORS

### dashboard.context_processors.site_settings
- Fetches SiteSetting singleton
- Makes available as `site_settings` in all templates
- Access: site_settings.site_name, contact_email, social URLs, etc.

---

## 11. ADMIN INTERFACE

Models registered for admin:
- **Accounts:** UserProfile
- **Academics:** Department, Course
- **Dashboard:** Course, Enrollment, Assignment, Submission, Grade, Ticket, Announcement, Document, StaffTask, StaffNote, SiteSetting, ActivityLog, Notification
- **News:** NewsPost
- **Events:** Event
- **Contact:** ContactMessage

---

## 12. TEMPLATE STRUCTURE

### Layout
```
templates/
├── base.html                    # Main template
├── admin/
│   ├── base_site.html
│   └── index.html
├── includes/
│   ├── footer.html
│   └── footer_connect.html
├── accounts/
│   ├── login.html
│   ├── register.html
│   ├── profile.html
│   ├── settings.html
│   └── password_*.html
├── academics/
│   ├── calendar.html
│   ├── course_detail.html
│   ├── department_detail.html
│   └── department_list.html
├── core/
│   ├── home.html
│   ├── about.html
│   ├── organization.html
│   ├── services.html
│   ├── admissions.html
│   ├── privacy.html
│   └── services/
├── dashboard/
│   ├── index.html
│   ├── student/
│   │   ├── index.html
│   │   ├── courses.html
│   │   ├── course_detail.html
│   │   ├── assignment_detail.html
│   │   ├── submit_assignment.html
│   │   ├── assignments.html
│   │   └── grades.html
│   ├── faculty/
│   │   ├── index.html
│   │   ├── courses_list.html
│   │   ├── course_form.html
│   │   ├── course_materials.html
│   │   ├── grade_submissions_list.html
│   │   ├── grade_form.html
│   │   ├── staff_tasks.html
│   │   └── staff_notes.html
│   └── staff/
│       ├── index.html
│       ├── students_list.html
│       ├── edit_student.html
│       ├── student_performance.html
│       ├── tickets_list.html
│       ├── ticket_detail.html
│       ├── announcements_list.html
│       ├── announcement_form.html
│       ├── documents_list.html
│       └── document_upload.html
├── news/
│   ├── news_list.html
│   └── news_detail.html
├── events/
│   ├── event_list.html
│   └── event_detail.html
└── contact/
    └── contact.html
```

---

## 13. DATA FLOW PATTERNS

### User Registration Flow
```
User → Register Form → 
Create User + auto-create UserProfile →
Set role in UserProfile →
Auto login → Redirect to profile
```

### Course Enrollment Flow
```
Student → View Available Courses →
Click Enroll → Create Enrollment →
Access course materials & assignments
```

### Assignment Submission Flow
```
Student → View Assignment →
Submit form (text/file) → Create Submission →
Faculty views submission → Grade it → Send feedback
```

### Support Ticket Flow
```
User → Create Ticket →
Staff reviews → Update status (open→progress→closed) →
User notified of resolution
```

---

## 14. DATABASE RELATIONSHIPS

```
User (Django)
├── UserProfile (1:1)
├── Created News Posts (1:N)
├── Enrollments (1:N)
├── Submissions (1:N)
├── Grades (1:N via Submission)
├── Created Tickets (1:N)
├── Created Announcements (1:N)
├── Uploaded Documents (1:N)
├── Assigned Tasks (1:N)
├── Created Tasks (1:N)
├── Notes (1:N)
├── Notifications (1:N)
└── Activity Logs (1:N)

Department
└── Courses (1:N)

Course (Dashboard)
├── Enrollments (1:N)
└── Assignments (1:N)

Assignment
└── Submissions (1:N)

Submission
└── Grade (1:1)

NewsPost
└── Category (many categories possible)

Event
└── Date based filtering
```

---

## 15. KEY FEATURES SUMMARY

### 1. Multi-Role System
- Students: Learn & submit work
- Faculty: Create courses & grade
- Staff: Manage students & support

### 2. Course Management
- Create & edit courses
- Upload assignments
- Track progress
- Grade submissions

### 3. Communication
- News posts with categories
- Event calendar
- Contact form
- Internal announcements
- Support tickets

### 4. User Management
- Registration with ID validation
- Profile management
- Role assignment
- Password management

### 5. Academic Organization
- Departments & courses
- Academic calendar
- Course requirements

### 6. Support System
- Ticket management
- Document sharing
- Staff task tracking
- Internal notes

---

## 16. RUNNING & DEPLOYMENT

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Create superuser
python manage.py createsuperuser

# Run migrations
python manage.py migrate

# Start server
python manage.py runserver
```

Server: http://127.0.0.1:8000/

### Deployment Checklist
- [ ] Change SECRET_KEY
- [ ] Set DEBUG = False
- [ ] Configure ALLOWED_HOSTS
- [ ] Set up HTTPS
- [ ] Use PostgreSQL instead of SQLite
- [ ] Configure email backend
- [ ] Set up logging
- [ ] Configure static file serving (CDN)
- [ ] Enable caching
- [ ] Set secure cookies
- [ ] Configure backup strategy

---

## 17. ADMIN COMMANDS

```bash
# Create superuser
python manage.py createsuperuser

# Run migrations
python manage.py migrate
python manage.py makemigrations

# Create sample data
python manage.py loaddata fixture_name

# Collect static files
python manage.py collectstatic

# Shell access
python manage.py shell

# View all URLs
python manage.py show_urls
```

---

## 18. COMMON PATTERNS

### View Protection
```python
@login_required
def staff_only_view(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard:index')
    # Logic here
```

### Query Optimization
```python
# Use select_related for ForeignKey
Course.objects.select_related('department')

# Use prefetch_related for reverse relationships
Course.objects.prefetch_related('assignments')

# Filter before accessing
User.objects.filter(is_staff=False)
```

### Slug Auto-Generation
```python
def save(self, *args, **kwargs):
    if not self.slug:
        self.slug = slugify(self.title)
    super().save(*args, **kwargs)
```

### Pagination
```python
from django.core.paginator import Paginator

paginator = Paginator(items, items_per_page)
page_obj = paginator.get_page(request.GET.get('page'))
```

---

## 19. SYSTEM REQUIREMENTS

### Minimum
- Python 3.8+
- Django 4.2+
- 100MB disk space
- SQLite (built-in)

### Recommended for Production
- Python 3.10+
- PostgreSQL 12+
- 1GB+ disk space
- Nginx/Apache
- Redis for caching
- Celery for async tasks

---

## 20. SECURITY CONSIDERATIONS

### Built-in Django Security
- CSRF protection (CsrfViewMiddleware)
- SQL injection prevention (ORM)
- XSS protection (template escaping)
- SQL injection through parameterized queries
- Password hashing (PBKDF2)

### Additional Measures
- Change SECRET_KEY in production
- Disable DEBUG in production
- Use HTTPS only
- Set SECURE_SSL_REDIRECT = True
- Implement rate limiting
- Validate all user inputs
- Use environment variables for secrets
- Regular security updates

---

## 21. PERFORMANCE OPTIMIZATION

### Database
- Use select_related() for ForeignKey
- Use prefetch_related() for ManyToMany & reverse FK
- Add database indexes on frequently queried fields
- Archive old data periodically

### Caching
- Enable Django cache framework
- Cache expensive queries
- Cache rendered templates
- Use Redis for production

### Assets
- Minify CSS/JavaScript
- Use CDN for static files
- Gzip compression
- Browser caching headers

---

## 22. EXTENSION POINTS

### Easy to Add
- New apps (faculty, staff modules)
- Additional user roles
- Custom forms & fields
- Email notifications
- Bulk operations
- Reporting & analytics
- API endpoints (DRF)

---

**System Design Created:** February 14, 2026  
**Base Framework:** Django 4.2.7  
**Database:** SQLite3 (portable to PostgreSQL/MySQL)
