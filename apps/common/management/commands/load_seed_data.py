from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
import random

User = get_user_model()

from apps.accounts.models import PatientProfile, DoctorProfile
from apps.scheduling.models import AppointmentSlot, DoctorWeeklySchedule
from apps.appointments.models import Appointment, AppointmentStatusHistory


class Command(BaseCommand):
    help = 'Load seed data using Django fixtures and create additional data'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Clear existing data before loading')
        parser.add_argument('--slots', type=int, default=20, help='Number of appointment slots to create')

    def handle(self, *args, **options):
        if options['clear']:
            self.clear_data()
        
        self.stdout.write('Loading fixture data...')
        try:
            call_command('loaddata', 'seed_data.json', app_label='common')
            self.stdout.write(self.style.SUCCESS('Fixture data loaded successfully!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error loading fixtures: {e}'))
            return
        
        # Set passwords for users
        self.set_passwords()
        
        # Create additional data
        self.create_doctor_schedules()
        self.create_appointment_slots(options['slots'])
        self.create_sample_appointments()
        
        self.stdout.write(self.style.SUCCESS('Seed data loading completed!'))
        self.print_credentials()

    def clear_data(self):
        """Clear existing data"""
        self.stdout.write('Clearing existing data...')
        
        models_to_clear = [
            'appointments.AppointmentStatusHistory',
            'appointments.Appointment',
            'scheduling.AppointmentSlot',
            'scheduling.DoctorWeeklySchedule',
            'accounts.PatientProfile',
            'accounts.ReceptionistProfile',
            'accounts.DoctorProfile',
            'accounts.AdminProfile',
            'accounts.User'
        ]
        
        for model_path in models_to_clear:
            try:
                app_label, model_name = model_path.split('.')
                model = __import__(f'apps.{app_label}.models', fromlist=[model_name])
                model_class = getattr(model, model_name)
                model_class.objects.all().delete()
                self.stdout.write(f'Cleared {model_name}')
            except Exception as e:
                self.stdout.write(f'Error clearing {model_path}: {e}')

    def set_passwords(self):
        """Set passwords for users"""
        self.stdout.write('Setting passwords...')
        
        passwords = {
            'amera': 'admin123',
            'admin': 'admin123',
            'dr_john_0': 'doctor123',
            'dr_sarah_1': 'doctor123',
            'dr_michael_2': 'doctor123',
            'rec_alice_0': 'reception123',
            'rec_bob_1': 'reception123',
            'patient_james_0': 'patient123',
            'patient_mary_1': 'patient123',
            'patient_patricia_2': 'patient123'
        }
        
        for username, password in passwords.items():
            try:
                user = User.objects.get(username=username)
                user.set_password(password)
                user.save()
                self.stdout.write(f'Set password for {username}')
            except User.DoesNotExist:
                self.stdout.write(f'User {username} not found')

    def create_doctor_schedules(self):
        """Create doctor weekly schedules"""
        self.stdout.write('Creating doctor schedules...')
        
        doctors = DoctorProfile.objects.all()
        
        for doctor in doctors:
            # Create schedule for Monday to Friday
            for day_num in range(0, 5):  # Monday to Friday
                if random.random() > 0.2:  # 80% chance doctor works this day
                    DoctorWeeklySchedule.objects.create(
                        doctor=doctor,
                        day_of_week=day_num,
                        start_time=datetime(2000, 1, 1, 9, 0).time(),  # 9:00 AM
                        end_time=datetime(2000, 1, 1, 17, 0).time(),   # 5:00 PM
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
            start_datetime = datetime.combine(date, datetime(2000, 1, 1, hour, minute).time())
            end_datetime = start_datetime + timedelta(minutes=30)
            
            AppointmentSlot.objects.create(
                doctor=doctor,
                slot_date=date,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                status=AppointmentSlot.Status.AVAILABLE
            )
        
        self.stdout.write(f'Created {count} appointment slots')

    def create_sample_appointments(self):
        """Create sample appointments"""
        self.stdout.write('Creating sample appointments...')
        
        patients = PatientProfile.objects.all()
        doctors = DoctorProfile.objects.all()
        
        # Create a few sample appointments
        for i in range(5):
            if not patients or not doctors:
                break
                
            patient = random.choice(patients)
            doctor = random.choice(doctors)
            
            # Find an available slot
            slot = AppointmentSlot.objects.filter(
                doctor=doctor,
                status=AppointmentSlot.Status.AVAILABLE,
                start_datetime__gte=timezone.now()
            ).first()
            
            if slot:
                # Create appointment
                appointment = Appointment.objects.create(
                    appointment_code=f"APT{1000 + i}",
                    patient=patient,
                    doctor=doctor,
                    slot=slot,
                    scheduled_start=slot.start_datetime,
                    scheduled_end=slot.end_datetime,
                    status=Appointment.Status.REQUESTED
                )
                
                # Update slot status
                slot.status = AppointmentSlot.Status.BOOKED
                slot.save()
                
                # Create status history
                AppointmentStatusHistory.objects.create(
                    appointment=appointment,
                    old_status=None,
                    new_status=Appointment.Status.REQUESTED,
                    changed_by=patient.user
                )
                
                self.stdout.write(f'Created appointment {appointment.appointment_code}')

    def print_credentials(self):
        """Print login credentials"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write('🏥 LOGIN CREDENTIALS')
        self.stdout.write('='*50)
        self.stdout.write('\n🔧 ADMIN USERS:')
        self.stdout.write('  Username: amera, Password: admin123')
        self.stdout.write('  Username: admin, Password: admin123')
        
        self.stdout.write('\n👨‍⚕️ DOCTOR USERS:')
        self.stdout.write('  Username: dr_john_0, Password: doctor123')
        self.stdout.write('  Username: dr_sarah_1, Password: doctor123')
        self.stdout.write('  Username: dr_michael_2, Password: doctor123')
        
        self.stdout.write('\n🏥 RECEPTIONIST USERS:')
        self.stdout.write('  Username: rec_alice_0, Password: reception123')
        self.stdout.write('  Username: rec_bob_1, Password: reception123')
        
        self.stdout.write('\n👤 PATIENT USERS:')
        self.stdout.write('  Username: patient_james_0, Password: patient123')
        self.stdout.write('  Username: patient_mary_1, Password: patient123')
        self.stdout.write('  Username: patient_patricia_2, Password: patient123')
        
        self.stdout.write('\n🌐 You can now login and test the application!')
        self.stdout.write('='*50)
