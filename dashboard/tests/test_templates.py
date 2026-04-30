from django.template.loader import get_template
from django.test import SimpleTestCase


class DashboardTemplateCompatibilityTests(SimpleTestCase):
    def test_legacy_admin_panel_users_list_template_exists(self):
        template = get_template("admin_panel/users_list.html")

        self.assertIsNotNone(template)
