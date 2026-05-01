# dashboard/tests/test_views.py

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from accounts.models import AdminProfile, DoctorProfile, ReceptionistProfile

User = get_user_model()


class DashboardViewsTest(TestCase):

    def setUp(self):
        self.client = Client()

        self.admin = User.objects.create_user(
            username='admin1',
            email='admin@clinic.com',
            password='clinic1234',
            first_name='Admin',
            last_name='User',
        )
        AdminProfile.objects.create(user=self.admin, employee_code='ADM-001')
        self.doctor = User.objects.create_user(
            username='doctor1',
            email='doctor@clinic.com',
            password='clinic1234',
            first_name='Ahmed',
            last_name='Samy',
        )
        DoctorProfile.objects.create(
            user=self.doctor,
            specialization='General Medicine',
            license_number='DOC-001',
        )
        self.receptionist = User.objects.create_user(
            username='reception1',
            email='reception@clinic.com',
            password='clinic1234',
            first_name='Nour',
            last_name='Ibrahim',
        )
        ReceptionistProfile.objects.create(user=self.receptionist, employee_code='REC-001')

    def test_admin_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard:admin'))
        self.assertNotEqual(response.status_code, 200)

    def test_admin_dashboard_accessible_with_permission(self):
        self.client.login(username='admin1', password='clinic1234')
        response = self.client.get(reverse('dashboard:admin'))
        self.assertEqual(response.status_code, 200)

    def test_admin_dashboard_forbidden_without_admin_role(self):
        self.client.login(username='doctor1', password='clinic1234')
        response = self.client.get(reverse('dashboard:admin'))
        self.assertEqual(response.status_code, 403)

    def test_doctor_dashboard_accessible_with_permission(self):
        self.client.login(username='doctor1', password='clinic1234')
        response = self.client.get(reverse('dashboard:doctor'))
        self.assertEqual(response.status_code, 200)

    def test_doctor_dashboard_forbidden_without_doctor_role(self):
        self.client.login(username='reception1', password='clinic1234')
        response = self.client.get(reverse('dashboard:doctor'))
        self.assertEqual(response.status_code, 403)

    def test_receptionist_dashboard_accessible_with_permission(self):
        self.client.login(username='reception1', password='clinic1234')
        response = self.client.get(reverse('dashboard:receptionist'))
        self.assertEqual(response.status_code, 200)

    def test_receptionist_dashboard_forbidden_without_receptionist_role(self):
        self.client.login(username='admin1', password='clinic1234')
        response = self.client.get(reverse('dashboard:receptionist'))
        self.assertEqual(response.status_code, 403)

    def test_export_appointments_requires_permission(self):
        self.client.login(username='doctor1', password='clinic1234')
        response = self.client.get(reverse('dashboard:export-appointments'))
        self.assertEqual(response.status_code, 403)

    def test_export_appointments_returns_csv(self):
        self.client.login(username='admin1', password='clinic1234')
        response = self.client.get(reverse('dashboard:export-appointments'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])

    def test_export_noshow_returns_csv(self):
        self.client.login(username='admin1', password='clinic1234')
        response = self.client.get(reverse('dashboard:export-noshow'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])

    def test_export_revenue_returns_csv(self):
        self.client.login(username='admin1', password='clinic1234')
        response = self.client.get(reverse('dashboard:export-revenue'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])

    def test_reports_page_hides_audit_log(self):
        self.client.login(username='admin1', password='clinic1234')
        response = self.client.get(reverse('dashboard:reports'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Appointment Reports')
        self.assertNotContains(response, 'Audit Log')
        self.assertNotContains(response, 'Audit Trail')

    def test_admin_dashboard_hides_recent_activity_panel(self):
        self.client.login(username='admin1', password='clinic1234')
        response = self.client.get(reverse('dashboard:admin'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Operations')
        self.assertNotContains(response, 'Recent Activity')
