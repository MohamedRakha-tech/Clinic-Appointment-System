# dashboard/tests/test_views.py

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

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
        self.doctor = User.objects.create_user(
            username='doctor1',
            email='doctor@clinic.com',
            password='clinic1234',
            first_name='Ahmed',
            last_name='Samy',
        )
        self.receptionist = User.objects.create_user(
            username='reception1',
            email='reception@clinic.com',
            password='clinic1234',
            first_name='Nour',
            last_name='Ibrahim',
        )

        self.admin.user_permissions.add(
            Permission.objects.get(codename='view_analytics'),
            Permission.objects.get(codename='export_data'),
        )
        self.doctor.user_permissions.add(
            Permission.objects.get(codename='view_doctor_dashboard'),
        )
        self.receptionist.user_permissions.add(
            Permission.objects.get(codename='view_receptionist_dashboard'),
        )

    def test_admin_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard:admin'))
        self.assertNotEqual(response.status_code, 200)

    def test_admin_dashboard_accessible_with_permission(self):
        self.client.login(username='admin1', password='clinic1234')
        response = self.client.get(reverse('dashboard:admin'))
        self.assertEqual(response.status_code, 200)

    def test_admin_dashboard_forbidden_without_permission(self):
        self.client.login(username='doctor1', password='clinic1234')
        response = self.client.get(reverse('dashboard:admin'))
        self.assertEqual(response.status_code, 403)

    def test_doctor_dashboard_accessible_with_permission(self):
        self.client.login(username='doctor1', password='clinic1234')
        response = self.client.get(reverse('dashboard:doctor'))
        self.assertEqual(response.status_code, 200)

    def test_doctor_dashboard_forbidden_without_permission(self):
        self.client.login(username='reception1', password='clinic1234')
        response = self.client.get(reverse('dashboard:doctor'))
        self.assertEqual(response.status_code, 403)

    def test_receptionist_dashboard_accessible_with_permission(self):
        self.client.login(username='reception1', password='clinic1234')
        response = self.client.get(reverse('dashboard:receptionist'))
        self.assertEqual(response.status_code, 200)

    def test_receptionist_dashboard_forbidden_without_permission(self):
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

    def test_export_audit_log_returns_csv(self):
        self.client.login(username='admin1', password='clinic1234')
        response = self.client.get(reverse('dashboard:export-audit-log'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])