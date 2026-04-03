# Render Deployment Notes

This project is ready to deploy on Render with the included [render.yaml](c:\Users\Admin\Documents\NELSIE DOCUMENTS FILE\bufia\render.yaml).

## Quick launch

1. Push this repository to GitHub.
2. In Render, create a new Blueprint and connect the repository.
3. Render will create:
   - one Python web service named `bufia`
   - one PostgreSQL database named `bufia-db`
4. Wait for the first deploy to finish.
5. Open `https://<your-service>.onrender.com/setup/` if no admin account exists yet.

## Existing data

The live Render database is PostgreSQL. Your local file [db.sqlite3](c:\Users\Admin\Documents\NELSIE DOCUMENTS FILE\bufia\db.sqlite3) is not used in production.

If you want your current records online, load a Django fixture into the Render database after the first deploy. This repo already contains [db_dump.json](c:\Users\Admin\Documents\NELSIE DOCUMENTS FILE\bufia\db_dump.json).

Typical Render shell commands:

```bash
python manage.py migrate
python manage.py loaddata db_dump.json
```

Only run `loaddata` if the fixture matches your latest local data.

## Uploaded files

User uploads in this app include profile images and payment slips. Static files are handled by WhiteNoise, but uploaded media is different:

- `free` web services can go online quickly, but uploaded media is stored on ephemeral disk and can disappear on redeploy or restart.
- If you need uploads to persist, switch the web service to a paid plan and add a persistent disk mounted at `/var/data`.

Then add this Render environment variable:

```text
RENDER_DISK_PATH=/var/data
```

The app will automatically store media in `/var/data/media`.
