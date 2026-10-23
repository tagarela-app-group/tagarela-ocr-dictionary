from django.test import TestCase

from apps.accounts.models import User


class UserManagerTests(TestCase):
    def test_create_user_lowercases_email_and_hashes_password(self):
        user = User.objects.create_user("Ana@Example.COM", "s3nha-forte-123", name="Ana")

        self.assertEqual(user.email, "ana@example.com")
        self.assertTrue(user.check_password("s3nha-forte-123"))
        self.assertFalse(user.is_staff)

    def test_create_user_without_password_has_unusable_password(self):
        user = User.objects.create_user("ana@example.com")

        self.assertFalse(user.has_usable_password())

    def test_create_user_without_email_fails(self):
        with self.assertRaises(ValueError):
            User.objects.create_user("")

    def test_create_superuser_is_staff_and_superuser(self):
        user = User.objects.create_superuser("admin@example.com", "s3nha-forte-123")

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_display_uses_name_or_email(self):
        self.assertEqual(str(User(email="ana@example.com", name="Ana")), "Ana")
        self.assertEqual(str(User(email="ana@example.com")), "ana@example.com")


class UserAdminTests(TestCase):
    def setUp(self):
        admin = User.objects.create_superuser("admin@example.com", "s3nha-forte-123")
        self.client.force_login(admin)

    def test_changelist_and_add_pages_render(self):
        for url in ["/admin/accounts/user/", "/admin/accounts/user/add/"]:
            with self.subTest(url):
                self.assertEqual(self.client.get(url).status_code, 200)
