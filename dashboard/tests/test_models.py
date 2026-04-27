from django.contrib.auth import get_user_model
from django.test import TestCase

from dashboard.models import AuditLog

User = get_user_model()


class AuditLogModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@clinic.com",
            password="clinic1234",
            first_name="Test",
            last_name="User",
        )

    def test_auditlog_created_via_log_method(self):
        log = AuditLog.log(
            user=self.user,
            action="CREATE",
            target_model="Appointment",
            target_id=1,
            description="Test log entry",
        )
        self.assertIsNotNone(log.pk)
        self.assertEqual(log.action, "CREATE")
        self.assertEqual(log.target_model, "Appointment")
        self.assertEqual(log.target_id, 1)

    def test_auditlog_str(self):
        log = AuditLog.log(
            user=self.user,
            action="UPDATE",
            target_model="User",
            target_id=self.user.pk,
        )
        self.assertIn("UPDATE", str(log))
        self.assertIn("User", str(log))

    def test_auditlog_without_user(self):
        log = AuditLog.log(
            user=None,
            action="LOGIN",
            target_model="User",
        )
        self.assertIsNone(log.user)
        self.assertEqual(log.action, "LOGIN")

    def test_auditlog_extra_data(self):
        log = AuditLog.log(
            user=self.user,
            action="EXPORT",
            target_model="Appointment",
            extra_data={"format": "csv", "rows": 50},
        )
        self.assertEqual(log.extra_data["format"], "csv")
        self.assertEqual(log.extra_data["rows"], 50)

    def test_auditlog_ordering(self):
        AuditLog.log(user=self.user, action="LOGIN", target_model="User")
        AuditLog.log(user=self.user, action="LOGOUT", target_model="User")
        logs = AuditLog.objects.all()
        self.assertEqual(logs[0].action, "LOGOUT")
