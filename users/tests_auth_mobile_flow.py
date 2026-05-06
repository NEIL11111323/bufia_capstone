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
            follow=True,
        )
        self.assertEqual(signup_response.redirect_chain[-1][0], reverse("dashboard"))
        self.assertEqual(signup_response.status_code, 200)
        self.assertTemplateUsed(signup_response, "users/dashboard.html")

        self.assertTrue(get_user_model().objects.filter(username=username).exists())

        self.client.logout()
        login_response = self.client.post(
            reverse("account_login"),
            {"login": username, "password": self.password},
            follow=True,
        )
        self.assertEqual(login_response.redirect_chain[-1][0], reverse("dashboard"))
        self.assertEqual(login_response.status_code, 200)
        self.assertTemplateUsed(login_response, "users/dashboard.html")

    def test_signup_allows_password_similar_but_not_exact_username_or_email(self):
        username = "Allen12"
        password = "Allengwapokaayu12!"
        response = self.client.post(
            reverse("account_signup"),
            {
                "username": username,
                "email": "Allengwapo@gmail.com",
                "password1": password,
                "password2": password,
                "accept_terms": "on",
            },
            follow=True,
        )

        self.assertEqual(response.redirect_chain[-1][0], reverse("dashboard"))
        self.assertTrue(get_user_model().objects.filter(username=username).exists())

    def test_signup_rejects_password_exactly_matching_username_with_clear_message(self):
        username = "AllenUser12"
        response = self.client.post(
            reverse("account_signup"),
            {
                "username": username,
                "email": "allenuser12@example.com",
                "password1": username,
                "password2": username,
                "accept_terms": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username=username).exists())
        self.assertContains(
            response,
            "Password: Your password must not be exactly the same as your username.",
        )

    def test_signup_rejects_password_exactly_matching_email_with_clear_message(self):
        email = "allenuser12@example.com"
        response = self.client.post(
            reverse("account_signup"),
            {
                "username": "AllenUser13",
                "email": email,
                "password1": email,
                "password2": email,
                "accept_terms": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username="AllenUser13").exists())
        self.assertContains(
            response,
            "Password: Your password must not be exactly the same as your email address.",
        )

    def test_operator_login_redirect_strips_staff_access(self):
        user_model = get_user_model()
        username = "mobileflow_operator"
        operator = user_model.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password=self.password,
            role=user_model.OPERATOR,
            is_staff=True,
            is_active=True,
        )

        login_response = self.client.post(
            reverse("account_login"),
            {"login": username, "password": self.password},
            follow=True,
        )

        self.assertEqual(
            login_response.redirect_chain[-1][0],
            reverse("dashboard"),
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertTemplateUsed(login_response, "users/dashboard.html")
        self.assertNotContains(login_response, "Complete Your Membership Application")

        operator.refresh_from_db()
        self.assertFalse(operator.is_staff)
