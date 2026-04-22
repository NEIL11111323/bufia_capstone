from unittest.mock import patch

from django.db import OperationalError
from django.test import TestCase
from django.urls import reverse


class SetupViewTests(TestCase):
    def test_setup_page_handles_database_initialization_errors_gracefully(self):
        with patch('bufia.views.setup_views.User.objects.filter') as mock_filter:
            mock_filter.return_value.exists.side_effect = OperationalError("db not ready")

            response = self.client.get(reverse('setup'))

        self.assertEqual(response.status_code, 503)
        self.assertContains(response, 'Setup is temporarily unavailable', status_code=503)
