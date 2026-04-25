# Clinic Appointment System

A production-grade Django REST API for comprehensive clinic appointment management with role-based access control, scheduling logic, and audit trails.

## Features

### Core Functionality
- **Appointment Booking & Management**: Complete lifecycle from booking to completion
- **Smart Scheduling**: Automatic slot generation with buffer time handling
- **Role-Based Access Control**: Patient, Doctor, Receptionist, and Admin permissions
- **Queue Management**: Real-time waiting room and doctor queue tracking
- **Audit Trails**: Complete history of status changes and rescheduling
- **EMR Integration**: Consultation records, prescriptions, and test requests

### Key Capabilities
- **Double-Booking Prevention**: Database constraints prevent overlapping appointments
- **Buffer Time Enforcement**: Configurable consultation and buffer times
- **Status Workflow**: REQUESTED → CONFIRMED → CHECKED_IN → COMPLETED
- **Cancellation Policies**: Role-based cancellation rules
- **Rescheduling with Validation**: Complete audit trail for all changes
- **Permission Controls**: Granular access based on user roles

## Requirements

- Python 3.12+
- MySQL 8+
- pip

## Installation

### 1. Clone and Setup Environment
```bash
git clone <repository-url>
cd Clinic-Appointment-System
cp .env.example .env
```

### 2. Configure Database
Update `.env` with your MySQL credentials:
```env
DB_ENGINE=django.db.backends.mysql
DB_NAME=clinic_db
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Setup
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5. Run Development Server
```bash
python manage.py runserver
```

## API Endpoints

### Authentication
- `POST /api/accounts/users/` - Register new user
- `GET /api/accounts/users/profile/` - Get current user profile

### Appointments
- `GET /api/appointments/appointments/` - List appointments (filtered by role)
- `POST /api/appointments/appointments/` - Book new appointment
- `GET /api/appointments/appointments/{id}/` - Get appointment details
- `POST /api/appointments/appointments/{id}/confirm/` - Confirm appointment
- `POST /api/appointments/appointments/{id}/check_in/` - Check-in patient
- `POST /api/appointments/appointments/{id}/complete/` - Complete appointment
- `POST /api/appointments/appointments/{id}/cancel/` - Cancel appointment
- `POST /api/appointments/appointments/{id}/reschedule/` - Reschedule appointment
- `GET /api/appointments/appointments/my_appointments/` - Get user's appointments
- `GET /api/appointments/appointments/search/` - Search appointments (staff only)

### Scheduling
- `GET /api/scheduling/slots/` - List appointment slots
- `GET /api/scheduling/slots/available/` - Get available slots
- `GET /api/scheduling/weekly-schedules/` - List doctor weekly schedules
- `POST /api/scheduling/slot-generation/generate/` - Generate slots
- `POST /api/scheduling/slot-generation/check_availability/` - Check availability

### Queue Management
- `GET /api/queueing/queues/doctor_queue/` - Get doctor queue
- `GET /api/queueing/queues/waiting_room/` - Get waiting room
- `GET /api/queueing/queues/today_schedule/` - Get today's schedule
- `GET /api/queueing/queues/overview/` - Get queue overview
- `POST /api/queueing/check-in/patient/` - Check-in patient

### EMR (Electronic Medical Records)
- `GET /api/emr/consultation-records/` - List consultation records
- `POST /api/emr/consultation-records/` - Create consultation record
- `GET /api/emr/consultation-records/{id}/prescription_items/` - Get prescriptions
- `GET /api/emr/consultation-records/{id}/requested_tests/` - Get requested tests

## User Roles & Permissions

### Patient
- Book available slots
- View own appointments
- Cancel REQUESTED/CONFIRMED appointments
- Request rescheduling
- View completed consultation summaries

### Doctor
- View own schedule and queue
- Confirm/decline appointment requests
- Check-in patients
- Complete appointments
- Create/edit consultation records
- Mark no-show

### Receptionist
- Manage doctor schedules
- Confirm bookings
- Check-in patients
- Reschedule appointments
- View all appointments (no medical notes access)

### Admin
- Full system access
- Manage users and roles
- Access analytics and reports
- Override restrictions

## Testing

### Run Unit Tests
```bash
python manage.py test apps.appointments.tests
```

### Run with Coverage
```bash
pytest --cov=apps.appointments --cov-report=html
```

### Test Coverage
The system includes comprehensive unit tests covering:
- Slot generation logic
- Double-booking prevention
- Permission-based status transitions
- Rescheduling with audit trail
- Buffer time enforcement
- Cancellation policies

## Database Schema

### Core Models
- **User**: Custom user model with profile relationships
- **PatientProfile**: Patient demographic information
- **DoctorProfile**: Doctor specialization and settings
- **AppointmentSlot**: Generated time slots with status tracking
- **Appointment**: Main appointment entity with audit trails
- **ConsultationRecord**: Medical records for completed appointments

### Key Constraints
- Unique appointment slots per doctor/time
- No overlapping appointments for same patient
- Completed appointments require consultation records
- Status transition validation

## Configuration

### Doctor Settings
- `consultation_duration_minutes`: Default appointment length (15 min)
- `buffer_before_minutes`: Pre-appointment buffer (5 min)
- `buffer_after_minutes`: Post-appointment buffer (5 min)

### Slot Generation
- Automatic slot generation based on weekly schedules
- Exception handling for vacations and special days
- Buffer time enforcement prevents overlaps

## Security Features

- Role-based permission system
- Database-level constraints
- Transaction-safe operations
- Audit trail for all changes
- Input validation and sanitization

## Development

### Project Structure
```
apps/
├── accounts/          # User management and authentication
├── appointments/     # Appointment booking and management
├── scheduling/       # Slot generation and scheduling
├── queueing/         # Queue management and check-in
├── emr/             # Electronic medical records
├── common/          # Shared utilities and permissions
└── notifications/   # Notification system
```

### Adding New Features
1. Create models in appropriate app
2. Add serializers for API responses
3. Implement viewsets with permission checks
4. Add unit tests
5. Update documentation

## Production Deployment

### Environment Variables
```env
DEBUG=False
SECRET_KEY=your-production-secret-key
ALLOWED_HOSTS=yourdomain.com
```

### Database Optimization
- Add indexes for frequently queried fields
- Use database connection pooling
- Implement caching for slot availability

### Security Considerations
- Use HTTPS in production
- Implement rate limiting
- Regular security updates
- Backup strategy for patient data

## API Examples

### Book an Appointment
```bash
curl -X POST http://localhost:8000/api/appointments/appointments/ \
  -H "Authorization: Token your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": 1,
    "doctor_id": 1,
    "slot_id": 1,
    "notes_for_staff": "First visit"
  }'
```

### Get Available Slots
```bash
curl -X GET "http://localhost:8000/api/scheduling/slots/available/?doctor_id=1&start_date=2024-01-15&end_date=2024-01-20" \
  -H "Authorization: Token your-token"
```

### Check-in Patient
```bash
curl -X POST http://localhost:8000/api/queueing/check-in/patient/ \
  -H "Authorization: Token your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "appointment_id": 1,
    "notes": "Patient arrived on time"
  }'
```

## Support

For issues and feature requests, please create an issue in the project repository.

## License

This project is licensed under the MIT License.
