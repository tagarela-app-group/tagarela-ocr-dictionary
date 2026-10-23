from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings


class AccountAdapter(DefaultAccountAdapter):
    def send_mail(self, template_prefix: str, email: str, context: dict) -> None:
        context = {**context, "code_minutes": settings.AUTH_CODE_TTL_SECONDS // 60}
        super().send_mail(template_prefix, email, context)

    def send_account_already_exists_mail(self, email: str) -> None:
        self.send_mail("account/email/account_already_exists", email, {})


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        parts = (data.get("first_name"), data.get("last_name"))
        full_name = " ".join(part for part in parts if part)
        user.name = (data.get("name") or full_name)[:150]

        return user
