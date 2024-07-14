# apps/bot_apps/management/commands/runbot.py
from django.core.management.base import BaseCommand
from apps.bot_apps.bot import dp
from aiogram import executor

class Command(BaseCommand):
    help = 'Запустить Telegram бота'

    def handle(self, *args, **options):
        executor.start_polling(dp, skip_updates=True)
