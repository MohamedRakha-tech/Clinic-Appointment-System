from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
import random
from decimal import Decimal

User = get_user_model()

from apps.accounts.models import PatientProfile, DoctorProfile, ReceptionistProfile, AdminProfile
from apps.appointments.models import Appointment, AppointmentStatusHistory, AppointmentRescheduleHistory
from apps.scheduling.models import AppointmentSlot, DoctorWeeklySchedule, DoctorScheduleException
from apps.emr.models import ConsultationRecord, PrescriptionItem
from apps.queueing.models import AppointmentCheckin


class Command(BaseCommand):
    help = 'Seed the database with test data for the clinic appointment system'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Clear existing data before seeding')
        parser.add_argument('--count', type=int, default=5, help='Number of records to create for each type')

    def handle(self, *args, **options):
        if options['clear']:
            self.clear_data()
        
        count = options['count']
        
        self.stdout.write(self.style.SUCCESS('Starting data seeding...'))
        
        # Create users and profiles
        self.create_admin_users()
        self.create_doctors(count)
        self.create_receptionists(2)
        self.create_patients(count * 3)
        
        # Create schedules and slots
        self.create_doctor_schedules()
        self.create_appointment_slots(count * 10)
        
        # Create appointments
        self.create_appointments(count * 5)
        
        # Create medical records
        self.create_medical_records(count * 3)
        
        # Create queue entries
        self.create_queue_entries(count * 2)
        
        self.stdout.write(self.style.SUCCESS('Data seeding completed successfully!'))

    def clear_data(self):
        """Clear existing data"""
        self.stdout.write('Clearing existing data...')
        
        models_to_clear = [
            AppointmentCheckin, ConsultationRecord, PrescriptionItem,
            AppointmentRescheduleHistory, AppointmentStatusHistory, Appointment,
            AppointmentSlot, DoctorScheduleException, DoctorWeeklySchedule,
            AdminProfile, ReceptionistProfile, PatientProfile, DoctorProfile,
            User
        ]
        
        for model in models_to_clear:
            model.objects.all().delete()
            self.stdout.write(f'Cleared {model.__name__}')

    def create_admin_users(self):
        """Create admin users"""
        self.stdout.write('Creating admin users...')
        
        admin_data = [
            {
                'username': 'amera',
                'email': 'ameraelsa3id2@gmail.com',
                'first_name': 'Amera',
                'last_name': 'Elsaid',
                'password': 'admin123'
            },
            {
                'username': 'admin',
                'email': 'admin@clinic.com',
                'first_name': 'System',
                'last_name': 'Administrator',
                'password': 'admin123'
            }
        ]
        
        for data in admin_data:
            user = User.objects.create_user(
                username=data['username'],
                email=data['email'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                password=data['password'],
                is_staff=True,
                is_superuser=True
            )
            AdminProfile.objects.create(user=user, employee_code=f"ADM{user.id:04d}")
            self.stdout.write(f'Created admin: {user.username}')

    def create_doctors(self, count):
        """Create doctor users and profiles"""
        self.stdout.write(f'Creating {count} doctors...')
        
        specialties = ['Cardiology', 'Neurology', 'Pediatrics', 'Orthopedics', 'Dermatology', 'Psychiatry', 'General Practice']
        first_names = ['John', 'Sarah', 'Michael', 'Emily', 'David', 'Lisa', 'Robert', 'Jennifer']
        last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis']
        
        for i in range(count):
            specialty = random.choice(specialties)
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            
            user = User.objects.create_user(
                username=f'dr_{first_name.lower()}_{i}',
                email=f'dr.{first_name.lower()}.{i}@clinic.com',
                first_name=first_name,
                last_name=last_name,
                password='doctor123'
            )
            
            DoctorProfile.objects.create(
                user=user,
                specialization=specialty,
                license_number=f"MD{random.randint(10000, 99999)}"
            )
            self.stdout.write(f'Created doctor: Dr. {user.first_name} {user.last_name} ({specialty})')

    def create_receptionists(self, count):
        """Create receptionist users and profiles"""
        self.stdout.write(f'Creating {count} receptionists...')
        
        first_names = ['Alice', 'Bob', 'Carol', 'David', 'Eve']
        last_names = ['Wilson', 'Taylor', 'Anderson', 'Thomas', 'Jackson']
        
        for i in range(count):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            
            user = User.objects.create_user(
                username=f'rec_{first_name.lower()}_{i}',
                email=f'rec.{first_name.lower()}.{i}@clinic.com',
                first_name=first_name,
                last_name=last_name,
                password='reception123'
            )
            
            ReceptionistProfile.objects.create(
                user=user,
                employee_code=f"REC{user.id:04d}"
            )
            self.stdout.write(f'Created receptionist: {user.first_name} {user.last_name}')

    def create_patients(self, count):
        """Create patient users and profiles"""
        self.stdout.write(f'Creating {count} patients...')
        
        first_names = ['James', 'Mary', 'Patricia', 'Robert', 'Jennifer', 'William', 'Linda', 'Richard']
        last_names = ['Moore', 'Taylor', 'Anderson', 'Thomas', 'Jackson', 'White', 'Harris', 'Martin']
        
        for i in range(count):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            
            user = User.objects.create_user(
                username=f'patient_{first_name.lower()}_{i}',
                email=f'patient.{first_name.lower()}.{i}@email.com',
                first_name=first_name,
                last_name=last_name,
                password='patient123'
            )
            
            PatientProfile.objects.create(
                user=user,
                date_of_birth=datetime(1980 + random.randint(18, 70), 
                                   random.randint(1, 12), 
                                   random.randint(1, 28)).date(),
                phone=f"+1{random.randint(2000000000, 9999999999)}",
                address=f"{random.randint(100, 999)} Main St, City {random.randint(1, 50)}, State {random.randint(1, 50)}",
                emergency_contact_name=f"{random.choice(first_names)} {random.choice(last_names)}",
                emergency_contact_phone=f"+1{random.randint(2000000000, 9999999999)}"
            )
            self.stdout.write(f'Created patient: {user.first_name} {user.last_name}')

    def create_doctor_schedules(self):
        """Create doctor schedules"""
        self.stdout.write('Creating doctor schedules...')
        
        doctors = DoctorProfile.objects.all()
        
        for doctor in doctors:
            # Create weekly schedule
            for day_num in range(0, 5):  # Monday to Friday (0-4)
                if random.random() > 0.2:  # 80% chance doctor works this day
                    DoctorWeeklySchedule.objects.create(
                        doctor=doctor,
                        day_of_week=day_num,
                        start_time=time(9, 0),  # 9:00 AM
                        end_time=time(17, 0),    # 5:00 PM
                        is_active=True
                    )
            
            self.stdout.write(f'Created schedule for Dr. {doctor.user.first_name} {doctor.user.last_name}')

    def create_appointment_slots(self, count):
        """Create appointment slots"""
        self.stdout.write(f'Creating {count} appointment slots...')
        
        doctors = DoctorProfile.objects.all()
        start_date = timezone.now().date()
        
        for i in range(count):
            doctor = random.choice(doctors)
            date = start_date + timedelta(days=random.randint(0, 30))
            
            # Random time between 9 AM and 5 PM
            hour = random.randint(9, 16)
            minute = random.choice([0, 15, 30, 45])
            start_time = datetime.combine(date, time(hour, minute))
            end_time = start_time + timedelta(minutes=30)
            
            AppointmentSlot.objects.create(
                doctor=doctor,
                start_datetime=start_time,
                end_datetime=end_time,
                status=AppointmentSlot.Status.AVAILABLE
            )
        
        self.stdout.write(f'Created {count} appointment slots')

    def create_appointments(self, count):
        """Create appointments"""
        self.stdout.write(f'Creating {count} appointments...')
        
        patients = PatientProfile.objects.all()
        doctors = DoctorProfile.objects.all()
        statuses = [Appointment.Status.REQUESTED, Appointment.Status.CONFIRMED, 
                   Appointment.Status.COMPLETED, Appointment.Status.CANCELLED]
        
        for i in range(count):
            patient = random.choice(patients)
            doctor = random.choice(doctors)
            status = random.choice(statuses)
            
            # Find available slot or create one
            slot = AppointmentSlot.objects.filter(
                doctor=doctor,
                status=AppointmentSlot.Status.AVAILABLE,
                start_datetime__gte=timezone.now()
            ).first()
            
            if not slot:
                # Create a new slot
                date = timezone.now().date() + timedelta(days=random.randint(0, 30))
                hour = random.randint(9, 16)
                minute = random.choice([0, 15, 30, 45])
                start_time = datetime.combine(date, time(hour, minute))
                end_time = start_time + timedelta(minutes=30)
                
                slot = AppointmentSlot.objects.create(
                    doctor=doctor,
                    start_datetime=start_time,
                    end_datetime=end_time,
                    status=AppointmentSlot.Status.AVAILABLE
                )
            
            # Update slot status if appointment is confirmed
            if status in [Appointment.Status.CONFIRMED, Appointment.Status.COMPLETED]:
                slot.status = AppointmentSlot.Status.BOOKED
                slot.save()
            
            appointment = Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                slot=slot,
                status=status,
                notes=random.choice([
                    'Regular checkup',
                    'Follow-up visit',
                    'New patient consultation',
                    'Urgent visit',
                    'Annual physical',
                    None
                ])
            )
            
            # Create status history
            AppointmentStatusHistory.objects.create(
                appointment=appointment,
                old_status=None,
                new_status=status,
                changed_by=doctor.user if status != Appointment.Status.REQUESTED else patient.user,
                changed_at=timezone.now() - timedelta(hours=random.randint(1, 24))
            )
        
        self.stdout.write(f'Created {count} appointments')

    def create_medical_records(self, count):
        """Create medical records"""
        self.stdout.write(f'Creating {count} medical records...')
        
        appointments = Appointment.objects.filter(status=Appointment.Status.COMPLETED)
        
        for i in range(min(count, appointments.count())):
            appointment = random.choice(appointments)
            
            # Create consultation record
            consultation_record = ConsultationRecord.objects.create(
                appointment=appointment,
                doctor=appointment.doctor,
                diagnosis=random.choice([
                    'Common cold', 'Hypertension', 'Diabetes Type 2', 'Migraine', 
                    'Gastroenteritis', 'Bronchitis', 'Allergic rhinitis', 'Anxiety'
                ]),
                notes=f"Patient reports {random.choice(['mild', 'moderate', 'severe'])} symptoms",
                requested_tests=random.choice([
                    'Blood test', 'X-ray', 'ECG', 'MRI', 'CT scan', None
                ]),
                summary_for_patient=f"Follow-up in {random.randint(1, 4)} weeks"
            )
            
            # Create prescription items
            if random.random() > 0.3:  # 70% chance of prescription
                for _ in range(random.randint(1, 3)):  # 1-3 prescription items
                    PrescriptionItem.objects.create(
                        consultation_record=consultation_record,
                        drug_name=random.choice([
                            'Amoxicillin 500mg', 'Ibuprofen 400mg', 'Acetaminophen 500mg',
                            'Lisinopril 10mg', 'Metformin 500mg', 'Atorvastatin 20mg',
                            'Omeprazole 20mg', 'Albuterol inhaler', 'Prednisone 5mg'
                        ]),
                        dose=random.choice(['1 tablet', '2 tablets', '1 capsule', '10ml']),
                        frequency=random.choice(['once daily', 'twice daily', 'three times daily', 'as needed']),
                        duration=random.choice(['7 days', '10 days', '14 days', '30 days']),
                        instructions="Take with food"
                    )
        
        self.stdout.write(f'Created {count} medical records')

    def create_queue_entries(self, count):
        """Create queue entries"""
        self.stdout.write(f'Creating {count} queue entries...')
        
        appointments = Appointment.objects.filter(status=Appointment.Status.CONFIRMED)
        
        for i in range(min(count, appointments.count())):
            appointment = random.choice(appointments)
            
            # Create check-in record
            AppointmentCheckin.objects.create(
                appointment=appointment,
                checked_in_at=timezone.now() - timedelta(minutes=random.randint(5, 120)),
                checked_in_by=appointment.doctor.user,
                queue_number=random.randint(1, 50),
                called_at=timezone.now() - timedelta(minutes=random.randint(1, 30)) if random.random() > 0.5 else None,
                served_at=timezone.now() - timedelta(minutes=random.randint(1, 15)) if random.random() > 0.7 else None
            )
        
        self.stdout.write(f'Created {count} queue entries')


def time(hour, minute):
    """Helper function to create time objects"""
    return datetime(2000, 1, 1, hour, minute).time()
