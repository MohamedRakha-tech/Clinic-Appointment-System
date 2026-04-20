# Clinic Appointment System

## Requirements

- Python 3.12+
- MySQL 8+
- pip

## Python Dependencies

Install project dependencies from `requirements.txt`:

```bash
pip install -r requirements.txt
```

This includes:

- `Django` for the web framework
- `python-dotenv` for loading environment variables from `.env`
- `Pillow` for image/photo field support in Django (`ImageField`)
- `mysqlclient` for MySQL database connectivity

## Environment Setup

1. Copy the env template and set your values:

```bash
cp .env.example .env
```

2. Update `.env` values for MySQL:

```env
DB_ENGINE=django.db.backends.mysql
DB_NAME=clinic_db
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

## Run Project

```bash
python manage.py migrate
python manage.py runserver
```
