from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from mail.models import Mailing, Recipient, Message
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Создание групп и прав доступа'

    def handle(self, *args, **kwargs):
        # Создаем группу менеджеров
        manager_group, created = Group.objects.get_or_create(name='Менеджер')

        if created:
            self.stdout.write(self.style.SUCCESS('Группа "Менеджеры" создана'))

            # Права на модели mail
        recipient_ct = ContentType.objects.get_for_model(Recipient)
        message_ct = ContentType.objects.get_for_model(Message)
        mailing_ct = ContentType.objects.get_for_model(Mailing)

        mail_permissions = [
            Permission.objects.get(codename='can_view_all_recipients', content_type=recipient_ct),
            Permission.objects.get(codename='can_view_all_messages', content_type=message_ct),
            Permission.objects.get(codename='can_view_all_mailings', content_type=mailing_ct),
            Permission.objects.get(codename='can_change_any_mailing', content_type=mailing_ct),
            Permission.objects.get(codename='can_delete_any_mailing', content_type=mailing_ct),
        ]

        # Права на пользователей (users)
        user_ct = ContentType.objects.get_for_model(User)
        user_permissions = [
            Permission.objects.get(codename='view_user', content_type=user_ct),
            Permission.objects.get(codename='change_user', content_type=user_ct),
        ]

        for perm in mail_permissions + user_permissions:
            manager_group.permissions.add(perm)
            self.stdout.write(f'Добавлено разрешение: {perm.codename}')
