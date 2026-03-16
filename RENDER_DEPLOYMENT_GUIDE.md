# BUFIA System - Render Deployment Guide

## Prerequisites

1. **GitHub Account** - Your code must be in a GitHub repository
2. **Render Account** - Sign up at https://render.com (free tier available)
3. **Stripe Account** - For payment processing (if using payments)

## Step 1: Prepare Your Repository

### 1.1 Create .gitignore (if not exists)

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Django
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal
/media
/staticfiles

# Environment variables
.env
.env.local
.env.production

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
```

### 1.2 Push to GitHub

```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

## Step 2: Create Render Account and Services

### 2.1 Sign Up
1. Go to https://render.com
2. Sign up with GitHub
3. Authorize Render to access your repositories

### 2.2 Create PostgreSQL Database

1. Click "New +" → "PostgreSQL"
2. Configure:
   - **Name**: `bufia-db`
   - **Database**: `bufia`
   - **User**: `bufia`
   - **Region**: Singapore (or closest to your users)
   - **Plan**: Free
3. Click "Create Database"
4. **IMPORTANT**: Copy the "Internal Database URL" - you'll need this

### 2.3 Create Web Service

1. Click "New +" → "Web Service"
2. Connect your GitHub repository
3. Configure:
   - **Name**: `bufia`
   - **Region**: Singapore
   - **Branch**: `main`
   - **Root Directory**: (leave empty)
   - **Runtime**: Python 3
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn bufia.wsgi:application`
   - **Plan**: Free

## Step 3: Configure Environment Variables

In your Render web service dashboard, go to "Environment" and add:

### Required Variables:

```
SECRET_KEY=your-secret-key-here-generate-a-long-random-string
DEBUG=False
DATABASE_URL=<paste-internal-database-url-from-step-2.2>
DJANGO_SETTINGS_MODULE=bufia.settings_production
```

### Optional Variables (if using Stripe):

```
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### Generate SECRET_KEY:

Run this in Python:
```python
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

Or use this online: https://djecrety.ir/

## Step 4: Deploy

1. Click "Create Web Service"
2. Render will automatically:
   - Install dependencies
   - Run migrations
   - Collect static files
   - Start the server

3. Monitor the deployment logs for any errors

## Step 5: Post-Deployment Setup

### 5.1 Create Superuser

1. Go to your Render dashboard
2. Click on your web service
3. Go to "Shell" tab
4. Run:
```bash
python manage.py createsuperuser
```

### 5.2 Test Your Site

1. Your site will be available at: `https://bufia.onrender.com`
2. Test admin login: `https://bufia.onrender.com/admin/`
3. Test main functionality

### 5.3 Configure Custom Domain (Optional)

1. In Render dashboard, go to "Settings"
2. Scroll to "Custom Domains"
3. Add your domain
4. Update DNS records as instructed

## Step 6: Update Settings for Production

### 6.1 Update ALLOWED_HOSTS

In `bufia/settings_production.py`, add your custom domain:

```python
ALLOWED_HOSTS = [
    '.onrender.com',
    'yourdomain.com',
    'www.yourdomain.com',
]
```

### 6.2 Update CSRF_TRUSTED_ORIGINS

```python
CSRF_TRUSTED_ORIGINS = [
    'https://*.onrender.com',
    'https://yourdomain.com',
    'https://www.yourdomain.com',
]
```

## Troubleshooting

### Build Fails

**Error**: `Permission denied: ./build.sh`
**Solution**: Make build.sh executable:
```bash
git update-index --chmod=+x build.sh
git commit -m "Make build.sh executable"
git push
```

### Static Files Not Loading

**Solution**: 
1. Check `STATIC_ROOT` and `STATIC_URL` in settings
2. Ensure WhiteNoise is in MIDDLEWARE
3. Run `python manage.py collectstatic` manually in Shell

### Database Connection Error

**Solution**:
1. Verify DATABASE_URL is correct
2. Check PostgreSQL database is running
3. Ensure `psycopg2-binary` is in requirements.txt

### Application Error 500

**Solution**:
1. Check logs in Render dashboard
2. Verify all environment variables are set
3. Check DEBUG=False is set
4. Review ALLOWED_HOSTS

## Maintenance

### Update Code

```bash
git add .
git commit -m "Your update message"
git push origin main
```

Render will automatically redeploy.

### Run Migrations

After pushing database changes:
1. Go to Render Shell
2. Run: `python manage.py migrate`

### View Logs

1. Go to Render dashboard
2. Click "Logs" tab
3. Monitor real-time logs

### Backup Database

1. Go to PostgreSQL database in Render
2. Click "Backups" tab
3. Create manual backup or schedule automatic backups

## Cost Optimization

### Free Tier Limitations:
- Web service spins down after 15 minutes of inactivity
- First request after spin-down takes 30-60 seconds
- 750 hours/month free (enough for 1 service)
- PostgreSQL: 1GB storage, 97 hours/month

### Upgrade to Paid:
- **Starter Plan**: $7/month
  - No spin-down
  - Faster performance
  - More resources

## Security Checklist

- [ ] DEBUG=False in production
- [ ] Strong SECRET_KEY
- [ ] HTTPS enabled (automatic on Render)
- [ ] ALLOWED_HOSTS configured
- [ ] CSRF_TRUSTED_ORIGINS configured
- [ ] Database credentials secure
- [ ] Stripe keys in environment variables
- [ ] Regular backups enabled
- [ ] Monitor logs for suspicious activity

## Support

- **Render Docs**: https://render.com/docs
- **Django Deployment**: https://docs.djangoproject.com/en/4.2/howto/deployment/
- **Render Community**: https://community.render.com/

## Quick Commands Reference

```bash
# Local development
python manage.py runserver

# Collect static files
python manage.py collectstatic

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Check deployment readiness
python manage.py check --deploy

# Test production settings locally
python manage.py runserver --settings=bufia.settings_production
```

## Success Checklist

- [ ] Code pushed to GitHub
- [ ] PostgreSQL database created on Render
- [ ] Web service created and deployed
- [ ] Environment variables configured
- [ ] Migrations run successfully
- [ ] Static files collected
- [ ] Superuser created
- [ ] Admin panel accessible
- [ ] Main site functional
- [ ] Payments working (if applicable)
- [ ] Custom domain configured (optional)

## Your Deployment URLs

- **Web Service**: https://bufia.onrender.com
- **Admin Panel**: https://bufia.onrender.com/admin/
- **Database**: (Internal URL in Render dashboard)

---

**Deployment Date**: _____________
**Deployed By**: _____________
**Version**: 1.0.0

Good luck with your deployment! 🚀
