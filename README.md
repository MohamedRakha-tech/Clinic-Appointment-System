# Clinic Appointment System

Clinic Appointment System is a Django-based web application for managing clinic operations across multiple roles. Patients can register and book appointments, receptionists can manage schedules and slot generation, doctors can review their schedules and consultations, and admins can manage users and dashboards.

## Tech Stack

- Python 3.12+
- Django 6
- Django REST Framework
- MySQL 8 by default through `.env`
- SQLite can be used for local development if you override the database settings
- HTML, CSS, Bootstrap 5, Bootstrap Icons
- Tailwind CSS via CDN in some templates

## Project Apps

- `accounts` for authentication, user roles, and profiles
- `appointments` for booking, rescheduling, and appointment history
- `dashboard` for admin, doctor, and receptionist dashboards
- `scheduling` for weekly schedules, exceptions, slot generation, and slot APIs
- `queueing` for reception and doctor queue views
- `emr` for consultation and medical-record related pages
- `notifications` for in-app notifications
- `reports` for reporting-related models and views

## Prerequisites

- Git
- Python 3.12 or newer
- `pip`
- `virtualenv` or `venv`
- MySQL 8+ if you want to use the default database configuration

## Clone the Repository

```bash
git clone <repo-url>
cd Clinic-Appointment-System
```

## Create and Activate a Virtual Environment

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

macOS / Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

## Install Dependencies

```bash
pip install -r requirements.txt
```

Current runtime packages in `requirements.txt`:

- `Django`
- `djangorestframework`
- `django-allauth[socialaccount]`
- `mysqlclient`
- `python-dotenv`
- `Pillow`
- `factory-boy`
- `asgiref`
- `sqlparse`

## Environment Variables

The project loads environment variables from `.env` using `python-dotenv`.

1. Copy the sample file:

```bash
copy .env.example .env
```

macOS / Linux:

```bash
cp .env.example .env
```

2. Update `.env` with your local values.

Minimum variables currently used by the project:

```env
DB_ENGINE=django.db.backends.mysql
DB_NAME=clinic_db
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

Based on the current local setup, the expected `.env` structure is:

```env
DB_ENGINE=django.db.backends.mysql
DB_NAME=clinic_db
DB_USER=root
DB_PASSWORD=<your-local-mysql-password>
DB_HOST=127.0.0.1
DB_PORT=3306

GOOGLE_CLIENT_ID=<your-google-client-id>
GOOGLE_CLIENT_SECRET=<your-google-client-secret>
```

Recommended additions for team setup, even though they are not currently read from settings:

```env
SECRET_KEY=
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
```

Notes:

- `SECRET_KEY` is currently hardcoded in `clinic/settings.py`, so changing `.env` will not override it unless settings are updated later.
- Google social login is configured through `django-allauth`; leave the Google variables blank if you are not testing Google sign-in.
- The checked-in `.env.example` currently does not include `GOOGLE_CLIENT_ID` or `GOOGLE_CLIENT_SECRET`, so the sample file should be expanded in a future cleanup.

## Database Setup

### Option 1: MySQL (current default)

The project defaults to MySQL through these settings:

```env
DB_ENGINE=django.db.backends.mysql
DB_NAME=clinic_db
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

Create the database before migrating:

```sql
CREATE DATABASE clinic_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Then run:

```bash
python manage.py makemigrations
python manage.py migrate
```

### Option 2: SQLite for local development

If you do not want to set up MySQL locally, you can point Django to SQLite by changing `.env` to:

```env
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=
```

Then run:

```bash
python manage.py migrate
```

## Seed and Demo Data

### Demo users and schedules

The project includes a seed command in `accounts`:

```bash
python manage.py seed_demo_data
```

Useful options:

```bash
python manage.py seed_demo_data --password Password123!
python manage.py seed_demo_data --days 7
python manage.py seed_demo_data --with-appointment
```

Fresh seed command defaults create:

- Admin: `admin_demo / Password123!`
- Doctor: `doctor_demo / Password123!`
- Receptionist: `reception_demo / Password123!`
- Patient 1: `patient_demo / Password123!`
- Patient 2: `patient_other / Password123!`

Note:

- The repo also contains `dev_role_credentials.txt`, but those credentials do not exactly match the `seed_demo_data` command output. For a fresh database, trust the command-generated credentials above.

### Historical appointment demo data

There is an additional command for dashboard-friendly historical appointment data:

```bash
python manage.py seed_appointments
```

Useful options:

```bash
python manage.py seed_appointments --months 36
python manage.py seed_appointments --seed 42
python manage.py seed_appointments --bootstrap
```

### Slot generation command

The scheduling app also includes:

```bash
python manage.py generate_slots
```

Useful options:

```bash
python manage.py generate_slots --days 30
python manage.py generate_slots --doctor-id 1
python manage.py generate_slots --start-date 2026-05-01 --end-date 2026-05-31
```

## Run the Development Server

```bash
python manage.py runserver
```

Default local URL:

```text
http://127.0.0.1:8001/
```

## Main URLs

### Accounts

- `/accounts/signup/`
- `/accounts/patient/signup/`
- `/accounts/login/`
- `/accounts/patient/login/`
- `/accounts/staff/login/`
- `/accounts/logout/`

### Role Dashboards

- `/accounts/dashboard/patient/`
- `/accounts/dashboard/doctor/`
- `/accounts/dashboard/reception/`
- `/accounts/dashboard/admin/`
- `/dashboard/`
- `/dashboard/admin/`
- `/dashboard/doctor/`
- `/dashboard/receptionist/`

### Scheduling

- `/scheduling/schedules/`
- `/scheduling/schedules/create/`
- `/scheduling/exceptions/`
- `/scheduling/exceptions/create/`
- `/scheduling/slots/`
- `/scheduling/generate-slots/`
- `/scheduling/my-schedule/`

### Appointments

- `/appointments/`
- `/appointments/book/`
- `/appointments/<id>/`
- `/appointments/<id>/history/`
- `/appointments/<id>/cancel/`
- `/appointments/<id>/reschedule/`

### API

- `/api/slots/`
- `/api/slots/<id>/`
- `/api/slots/available/`
- `/api/appointments/`
- `/api/appointments/<id>/`

## Scheduling Flow for QA / Manual Testing

1. Log in as an admin or receptionist using `/accounts/staff/login/`.
2. Create at least one doctor user and doctor profile, or run `python manage.py seed_demo_data`.
3. Open `/scheduling/schedules/create/` and create a weekly schedule for a doctor.
4. Optionally add a schedule exception at `/scheduling/exceptions/create/`.
5. Generate slots from `/scheduling/generate-slots/` or with `python manage.py generate_slots`.
6. Review generated slots at `/scheduling/slots/`.
7. Check the doctor view at `/scheduling/my-schedule/`.
8. Test the slot API endpoints after logging in.

## API Authentication Note

The REST API is protected with `IsAuthenticated` in Django REST Framework settings, and the slot API viewset also enforces authenticated access.

For browser testing with session authentication:

1. Log in first at `/accounts/staff/login/` or another valid login page.
2. In the same browser session, visit `/api/slots/`, `/api/slots/<id>/`, or `/api/slots/available/`.

If you are not authenticated, the API will reject the request.

## Static Files

Static assets are configured with:

- `STATIC_URL = 'static/'`
- `STATICFILES_DIRS = [BASE_DIR / 'static']`

Project static files currently include:

- `static/css/style.css`
- `static/css/auth.css`
- `static/css/scheduling.css`
- `static/js/app.js`
- `static/images/image.jpg`

For local development, `runserver` is enough. For production-style deployment you would also run:

```bash
python manage.py collectstatic
```

## Migrations

Existing migrations are present for:

- `accounts`
- `appointments`
- `dashboard`
- `emr`
- `notifications`
- `queueing`
- `scheduling`

The `reports` app has a migrations package but no concrete migration file yet.

## Testing Commands

Basic project checks:

```bash
python manage.py check
python manage.py test
```

Run scheduling tests only:

```bash
python manage.py test scheduling
```

Other app-specific test examples:

```bash
python manage.py test accounts
python manage.py test appointments
python manage.py test dashboard
```

## Git Workflow

```bash
git pull origin main
git checkout -b feature/your-feature
git add .
git commit -m "message"
git push origin feature/your-feature
```

## Troubleshooting

### Missing dependencies

- Make sure the virtual environment is activated before running `pip install -r requirements.txt`.
- If `mysqlclient` fails to install, verify your MySQL client libraries and compiler tools are installed for your OS.

### Database connection errors

- Confirm MySQL is running.
- Confirm `.env` values match your local database credentials.
- If you want a quick local setup, switch to SQLite in `.env`.

### Migration errors

- Run `python manage.py migrate`.
- If models changed locally, run `python manage.py makemigrations` before `migrate`.
- Make sure the selected database exists before migrating.

### Static files not loading

- Confirm `django.contrib.staticfiles` is enabled.
- Confirm the `static/` directory exists and paths in templates use `{% load static %}`.
- For production-like environments, run `python manage.py collectstatic`.

### Authentication required for API

- Log in first using `/accounts/staff/login/` or another valid login route.
- Then test `/api/slots/` in the same session.

### No slots generated

- Make sure at least one active weekly schedule exists for a doctor.
- Add schedules first at `/scheduling/schedules/create/`.
- Then run slot generation again.

## Recommended First-Run Commands

After cloning, the safest order is:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py seed_demo_data --with-appointment
python manage.py runserver
```

If you use MySQL, create `clinic_db` first. If you use SQLite, update `.env` before running migrations.
