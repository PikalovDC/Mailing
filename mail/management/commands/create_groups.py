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
            self.stdout.write(self.style.SUCCESS('Группа "Менеджер" создана'))
        else:
            self.stdout.write('Группа "Менеджер" уже существует')

        # Получаем content types для моделей
        mailing_ct = ContentType.objects.get_for_model(Mailing)
        recipient_ct = ContentType.objects.get_for_model(Recipient)
        user_ct = ContentType.objects.get_for_model(User)

        # Права для менеджера
        manager_permissions = [
            # Просмотр всех рассылок
            Permission.objects.get(codename='view_mailing', content_type=mailing_ct),
            # Просмотр всех получателей
            Permission.objects.get(codename='view_recipient', content_type=recipient_ct),
            # Просмотр пользователей
            Permission.objects.get(codename='view_user', content_type=user_ct),
            # Блокировка пользователей (изменение is_active)
            Permission.objects.get(codename='change_user', content_type=user_ct),
        ]

        # Назначаем права группе
        for perm in manager_permissions:
            manager_group.permissions.add(perm)
            self.stdout.write(f'Добавлено разрешение: {perm.codename}')

        self.stdout.write(self.style.SUCCESS('Настройка группы "Менеджер" завершена'))
