from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import MailingAttempt, Mailing
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)


class MailingService:
    """Сервис для работы с рассылками"""

    @staticmethod
    def send_mailing(mailing):
        """
        Отправляет рассылку всем получателям
        """
        # Проверка времени
        now = timezone.now()
        if now < mailing.start_time or now > mailing.end_time:
            raise ValueError('Рассылка может быть отправлена только в период между start_time и end_time')

        results = []
        for recipient in mailing.recipients.all():
            result = MailingService._send_to_recipient(mailing, recipient)
            results.append(result)

        if mailing.periodicity != 'once':
            MailingService._create_next_mailing(mailing)

        return results

    @staticmethod
    def _create_next_mailing(mailing):
        """Создает следующую рассылку на основе периодичности"""
        if mailing.periodicity == 'daily':
            delta = timedelta(days=1)
        elif mailing.periodicity == 'weekly':
            delta = timedelta(days=7)
        elif mailing.periodicity == 'monthly':
            delta = timedelta(days=30)
        else:
            return

        next_mailing = Mailing.objects.create(
            start_time=mailing.start_time + delta,
            end_time=mailing.end_time + delta,
            periodicity=mailing.periodicity,
            message=mailing.message,
            owner=mailing.owner,
        )
        next_mailing.recipients.set(mailing.recipients.all())

    @staticmethod
    def _send_to_recipient(mailing, recipient):
        """
        Отправляет письмо одному получателю и создает запись о попытке
        """
        try:
            # Отправка письма
            send_mail(
                subject=mailing.message.subject,
                message=mailing.message.body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient.email],
                fail_silently=False,
            )

            # СОЗДАЕМ ЗАПИСЬ О ПОПЫТКЕ
            attempt = MailingAttempt.objects.create(
                status='success',
                server_response='Письмо успешно отправлено',
                related_mailing=mailing
            )
            return {'recipient': recipient, 'success': True, 'attempt': attempt}

        except Exception as e:
            logger.error(f'Ошибка отправки письма {recipient.email}: {e}')

            attempt = MailingAttempt.objects.create(
                status='failed',
                server_response=str(e),
                related_mailing=mailing
            )
            return {'recipient': recipient, 'success': False, 'error': e, 'attempt': attempt}

    @staticmethod
    def get_active_count():
        """Возвращает количество активных рассылок"""
        from django.utils import timezone
        from .models import Mailing

        now = timezone.now()
        return Mailing.objects.filter(
            start_time__lte=now,
            end_time__gte=now,
            status='started'
        ).count()
