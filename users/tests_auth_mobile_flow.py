from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AuthMobileFlowTests(TestCase):
    def setUp(self):
        self.password = "BufiaTest#123"

    def _signup_payload(self, username="mobileflow_user", accept_terms=True):
        payload = {
            "username": username,
            "email": f"{username}@example.com",
            "password1": self.password,
            "password2": self.password,
        }
        if accept_terms:
            payload["accept_terms"] = "on"
        return payload

    def test_signup_page_loads_with_terms_checkbox(self):
        response = self.client.get(reverse("account_signup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Account")
        self.assertContains(response, 'name="accept_terms"')

    def test_signup_requires_terms_acceptance(self):
        username = "mobileflow_noterms"
        response = self.client.post(
            reverse("account_signup"),
            self._signup_payload(username=username, accept_terms=False),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username=username).exists())
        self.assertContains(response, "Terms")

    def test_new_user_can_signup_then_login(self):
        username = "mobileflow_success"
        signup_response = self.client.post(
            reverse("account_signup"),
            self._signup_payload(username=username, accept_terms=True),
        )
        self.assertEqual(signup_response.status_code, 302)
        self.assertEqual(signup_response["Location"], reverse("dashboard"))

        self.assertTrue(get_user_model().objects.filter(username=username).exists())

        self.client.logout()
        login_response = self.client.post(
            reverse("account_login"),
            {"login": username, "password": self.password},
        )
        self.assertEqual(login_response.status_code, 302)
        self.assertEqual(login_response["Location"], reverse("dashboard"))

