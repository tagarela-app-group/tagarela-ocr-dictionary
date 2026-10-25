from django.urls import path

from apps.accounts.views import account

urlpatterns = [
    path("account", account, name="account"),
]
