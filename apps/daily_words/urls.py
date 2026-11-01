from django.urls import path

from apps.daily_words.views import daily_word, save_daily_word

urlpatterns = [
    path("daily-word", daily_word, name="daily_word"),
    path("daily-word/save", save_daily_word, name="daily_word_save"),
]
