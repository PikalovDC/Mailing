from django.core.management.base import BaseCommand
from mail.models import Mailing
from mail.services import MailingService


class Command(BaseCommand):
    help = 'Запустить рассылку'

    def add_arguments(self, parser):
        parser.add_argument('mailing_id', type=int)

    def handle(self, *args, **options):
        mailing = Mailing.objects.get(id=options['mailing_id'])
        results = MailingService.send_mailing(mailing)

        success = sum(1 for r in results if r['success'])
        self.stdout.write(f'Успешно: {success}')
