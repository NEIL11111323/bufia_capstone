# BUFIA Render Deployment - Quick Checklist

## ✅ Pre-Deployment (Do This First)

- [ ] All code committed to Git
- [ ] `.gitignore` file created
- [ ] `requirements.txt` updated with production dependencies
- [ ] `build.sh` created and executable
- [ ] `render.yaml` created
- [ ] Production settings file created
- [ ] Push all changes to GitHub

```bash
git add .
git commit -m "Ready for Render deployment"
git push origin main
```

## ✅ Render Setup (15 minutes)

### 1. Create Account
- [ ] Sign up at https://render.com
- [ ] Connect GitHub account

### 2. Create Database (5 min)
- [ ] New → PostgreSQL
- [ ] Name: `bufia-db`
- [ ] Region: Singapore
- [ ] Plan: Free
- [ ] **Copy Internal Database URL**

### 3. Create Web Service (10 min)
- [ ] New → Web Service
- [ ] Connect repository
- [ ] Name: `bufia`
- [ ] Build: `./build.sh`
- [ ] Start: `gunicorn bufia.wsgi:application`
- [ ] Plan: Free

### 4. Environment Variables
Add these in Render dashboard:

```
SECRET_KEY=<generate-random-50-char-string>
DEBUG=False
DATABASE_URL=<paste-database-url-from-step-2>
DJANGO_SETTINGS_MODULE=bufia.settings_production
```

Optional (Stripe):
```
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
```

## ✅ Post-Deployment (5 minutes)

### 1. Wait for Build
- [ ] Monitor logs for successful deployment
- [ ] Check for any errors

### 2. Create Superuser
In Render Shell:
```bash
python manage.py createsuperuser
```

### 3. Test Site
- [ ] Visit: https://bufia.onrender.com
- [ ] Test admin: https://bufia.onrender.com/admin/
- [ ] Test login
- [ ] Test main features

## ✅ Common Issues & Fixes

### Build.sh Permission Error
```bash
git update-index --chmod=+x build.sh
git commit -m "Fix build.sh permissions"
git push
```

### Static Files Not Loading
Check in Render Shell:
```bash
python manage.py collectstatic --no-input
```

### Database Connection Error
- Verify DATABASE_URL is correct
- Check PostgreSQL is running

## 🎉 Success!

Your site is live at: **https://bufia.onrender.com**

### Next Steps:
1. Configure custom domain (optional)
2. Set up automatic backups
3. Monitor logs regularly
4. Update ALLOWED_HOSTS for custom domain

---

**Total Time**: ~20-30 minutes
**Cost**: FREE (with limitations)
**Upgrade**: $7/month for no spin-down
