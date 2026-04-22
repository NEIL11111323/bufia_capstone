from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class GeneralReportsDashboardTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='general-reports-admin',
            email='general-reports-admin@example.com',
            password='testpass123',
        )
        self.client.force_login(self.admin)

    def test_dashboard_loads_and_keeps_reports_nav_open(self):
        response = self.client.get(reverse('general_reports:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Administrative Reporting Center')
        self.assertContains(response, 'Reports Overview')
