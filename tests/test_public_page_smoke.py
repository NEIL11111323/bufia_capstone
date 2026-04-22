from django.test import TestCase
from django.urls import reverse


class PublicPageSmokeTests(TestCase):
    def test_home_page_renders(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_login_page_renders(self):
        response = self.client.get(reverse('account_login'))
        self.assertEqual(response.status_code, 200)

    def test_signup_page_renders(self):
        response = self.client.get(reverse('account_signup'))
        self.assertEqual(response.status_code, 200)
