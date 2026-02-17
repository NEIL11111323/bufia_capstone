# BUFIA Management System

A comprehensive web-based solution for managing machine rentals and rice mill operations for Bawayan United Farmers Irrigations Incorporated.

## Features

- User Authentication and Authorization
- Machine Rental Management
- Rice Mill Scheduling
- Notification System
- Reporting and Analytics
- Mobile-friendly Interface

## Technology Stack

- Django 4.2.7
- MySQL
- Bootstrap 5
- JavaScript/jQuery
- HTML5/CSS3

## Prerequisites

- Python 3.11 (recommended)
- MySQL Server 8.x (or MariaDB 10.4+)
- Virtual Environment (venv)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd bufia
```

2. Create and activate virtual environment:
```bash
python -m venv .venv
# Linux/Mac
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create MySQL database (and user if needed):
```sql
CREATE DATABASE bufia_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- optionally create a dedicated user
CREATE USER 'bufia'@'localhost' IDENTIFIED BY 'strong-password';
GRANT ALL PRIVILEGES ON bufia_db.* TO 'bufia'@'localhost';
FLUSH PRIVILEGES;
```

5. Configure database connection (settings.py uses MySQL):
Update `bufia/settings.py` `DATABASES['default']` or export environment variables via `.env` (if you add `python-dotenv` loading):
```
DEBUG=True
SECRET_KEY=your-secret-key
DB_NAME=bufia_db
DB_USER=bufia
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=3306
```

6. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

7. Create superuser:
```bash
python manage.py createsuperuser
```

8. Run development server:
```bash
python manage.py runserver
```

Notes:
- If you encounter `ModuleNotFoundError: No module named 'django'`, ensure your virtual environment is activated and `pip install -r requirements.txt` ran successfully.
- On Windows, ensure that MySQL client libraries are available for `mysqlclient`. You may need to install Visual C++ Build Tools.

## Project Structure

```
bufia/
├── bufia/              # Project settings
├── users/              # User management
├── machines/           # Machine rental management
├── rice_mill/          # Rice mill scheduling
├── notifications/      # Notification system
├── static/            # Static files
├── templates/         # HTML templates
├── media/            # User uploaded files
└── manage.py         # Django management script
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 