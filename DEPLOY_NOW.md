# 🚀 Deploy BUFIA to Render NOW - Step by Step

## ✅ Step 1: Code is Ready (DONE)
Your deployment files are now on GitHub at:
https://github.com/NEIL11111323/bufia_capstone

## 📋 Step 2: Create Render Account (5 minutes)

1. **Go to Render**: https://render.com
2. **Click "Get Started"**
3. **Sign up with GitHub**
4. **Authorize Render** to access your repositories

## 🗄️ Step 3: Create PostgreSQL Database (5 minutes)

1. In Render Dashboard, click **"New +"** (top right)
2. Select **"PostgreSQL"**
3. Fill in:
   ```
   Name: bufia-db
   Database: bufia
   User: bufia
   Region: Singapore (or closest to you)
   PostgreSQL Version: 15
   Plan: Free
   ```
4. Click **"Create Database"**
5. **WAIT** for database to be created (1-2 minutes)
6. **IMPORTANT**: Click on the database, scroll down to "Connections"
7. **COPY** the "Internal Database URL" (starts with `postgresql://`)
   - Example: `postgresql://bufia:xxxxx@dpg-xxxxx/bufia`
   - **Save this somewhere - you'll need it in Step 5!**

## 🌐 Step 4: Create Web Service (5 minutes)

1. Click **"New +"** again
2. Select **"Web Service"**
3. Click **"Connect a repository"**
4. Find and select: **NEIL11111323/bufia_capstone**
5. Click **"Connect"**
6. Fill in the configuration:
   ```
   Name: bufia
   Region: Singapore
   Branch: development (or main)
   Root Directory: (leave empty)
   Runtime: Python 3
   Build Command: ./build.sh
   Start Command: gunicorn bufia.wsgi:application
   Plan: Free
   ```
7. **DON'T CLICK CREATE YET!** Scroll down to Environment Variables first

## 🔐 Step 5: Add Environment Variables (5 minutes)

Still on the same page, scroll to **"Environment Variables"** section.

Click **"Add Environment Variable"** and add these ONE BY ONE:

### Variable 1: SECRET_KEY
```
Key: SECRET_KEY
Value: django-insecure-your-secret-key-here-make-it-long-and-random-50-characters
```
**Generate a random one**: https://djecrety.ir/ (copy the generated key)

### Variable 2: DEBUG
```
Key: DEBUG
Value: False
```

### Variable 3: DATABASE_URL
```
Key: DATABASE_URL
Value: <PASTE THE URL YOU COPIED IN STEP 3>
```
Example: `postgresql://bufia:xxxxx@dpg-xxxxx/bufia`

### Variable 4: DJANGO_SETTINGS_MODULE
```
Key: DJANGO_SETTINGS_MODULE
Value: bufia.settings_production
```

### Optional - If using Stripe payments:
```
Key: STRIPE_PUBLIC_KEY
Value: pk_test_your_stripe_public_key

Key: STRIPE_SECRET_KEY
Value: sk_test_your_stripe_secret_key

Key: STRIPE_WEBHOOK_SECRET
Value: whsec_your_webhook_secret
```

## 🎯 Step 6: Deploy! (10-15 minutes)

1. After adding all environment variables, click **"Create Web Service"**
2. Render will start building your app
3. **Watch the logs** - you'll see:
   - Installing dependencies
   - Collecting static files
   - Running migrations
   - Starting server
4. **WAIT** for "Your service is live 🎉" message
5. If you see errors, check the logs and fix them

## 👤 Step 7: Create Admin User (2 minutes)

1. In your web service dashboard, click **"Shell"** tab (top menu)
2. Wait for shell to connect
3. Type this command:
   ```bash
   python manage.py createsuperuser
   ```
4. Enter:
   - Username: `admin`
   - Email: `admin@bufia.com`
   - Password: (choose a strong password)
   - Password confirmation: (same password)

## 🎉 Step 8: Test Your Site!

Your site is now live at: **https://bufia.onrender.com**

Test these URLs:
1. **Main site**: https://bufia.onrender.com
2. **Admin panel**: https://bufia.onrender.com/admin/
3. **Login** with the superuser you created

## ⚠️ Common Issues & Solutions

### Issue 1: Build fails with "Permission denied: ./build.sh"
**Solution**: The file needs to be executable. Run locally:
```bash
git update-index --chmod=+x build.sh
git add build.sh
git commit -m "Make build.sh executable"
git push origin development
```
Then redeploy in Render.

### Issue 2: Static files not loading (no CSS)
**Solution**: In Render Shell, run:
```bash
python manage.py collectstatic --no-input
```

### Issue 3: Database connection error
**Solution**: 
- Check DATABASE_URL is correct
- Make sure PostgreSQL database is running
- Verify the URL starts with `postgresql://`

### Issue 4: Page shows "Bad Request (400)"
**Solution**: Add your Render URL to ALLOWED_HOSTS
1. Go to `bufia/settings_production.py`
2. Add your URL to ALLOWED_HOSTS
3. Commit and push

## 📱 Step 9: Update for Your Custom Domain (Optional)

If you want to use your own domain (e.g., bufia.com):

1. In Render dashboard, go to your web service
2. Click **"Settings"**
3. Scroll to **"Custom Domains"**
4. Click **"Add Custom Domain"**
5. Enter your domain
6. Follow DNS instructions provided

## 💰 Free Tier Limitations

- **Spin down**: Service sleeps after 15 min of inactivity
- **First request**: Takes 30-60 seconds to wake up
- **Database**: 1GB storage, 97 hours/month
- **Bandwidth**: 100GB/month

**Upgrade to Starter ($7/month)** for:
- No spin down
- Faster performance
- Better reliability

## 🔄 How to Update Your Site Later

Whenever you make changes:
```bash
git add .
git commit -m "Your update message"
git push origin development
```
Render will automatically redeploy!

## 📊 Monitor Your Site

- **Logs**: Click "Logs" tab in Render dashboard
- **Metrics**: Click "Metrics" tab
- **Events**: Click "Events" tab

## ✅ Success Checklist

- [ ] Render account created
- [ ] PostgreSQL database created
- [ ] Database URL copied
- [ ] Web service created
- [ ] All environment variables added
- [ ] Deployment successful
- [ ] Superuser created
- [ ] Admin panel accessible
- [ ] Main site working
- [ ] Test all features

## 🆘 Need Help?

- **Render Docs**: https://render.com/docs
- **Render Community**: https://community.render.com
- **Django Deployment**: https://docs.djangoproject.com/en/4.2/howto/deployment/

---

## 🎯 Your Deployment Info

**Repository**: https://github.com/NEIL11111323/bufia_capstone
**Branch**: development
**Live URL**: https://bufia.onrender.com (after deployment)
**Admin URL**: https://bufia.onrender.com/admin/

**Estimated Total Time**: 30-40 minutes
**Cost**: FREE

---

Good luck! Your BUFIA system will be live soon! 🚀
