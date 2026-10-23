from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    def send_account_already_exists_mail(self, email: str) -> None:
        self.send_mail("account/email/account_already_exists", email, {})


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        parts = (data.get("first_name"), data.get("last_name"))
        full_name = " ".join(part for part in parts if part)
        user.name = (data.get("name") or full_name)[:150]

        return user
