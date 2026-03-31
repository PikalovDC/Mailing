from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings


class Recipient(models.Model):
    """Модель получателя рассылки"""
    email = models.EmailField(unique=True, verbose_name='Email')
    full_name = models.CharField(max_length=255, verbose_name='Ф.И.О.')
    comment = models.TextField(blank=True, null=True, verbose_name='Комментарий')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recipients',
        verbose_name='Владелец',
        null=True
    )

    def __str__(self):
        return f"({self.full_name}) {self.email}"

    class Meta:
        verbose_name = "Получатель"
        verbose_name_plural = "Получатели"
        permissions = [
            ('can_view_all_recipients', 'Может просматривать всех получателей'),
        ]


class Message(models.Model):
    """Модель сообщения для рассылки"""
    subject = models.CharField(max_length=255, verbose_name='Тема письма')
    body = models.TextField(verbose_name='Тело письма')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Владелец',
        null=True
    )

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        permissions = [
            ('can_view_all_messages', 'Может просматривать все сообщения'),
        ]

    def __str__(self):
        return self.subject


class Mailing(models.Model):
    """Модель рассылки"""
    STATUS_CHOICES = [
        ('created', 'Создана'),
        ('started', 'Запущена'),
        ('completed', 'Завершена'),
    ]

    PERIODICITY_CHOICES = [
        ('once', 'Однократная'),
        ('daily', 'Ежедневная'),
        ('weekly', 'Еженедельная'),
        ('monthly', 'Ежемесячная'),
    ]

    start_time = models.DateTimeField(verbose_name='Дата и время начала')
    end_time = models.DateTimeField(verbose_name='Дата и время окончания')
    periodicity = models.CharField(
        max_length=20,
        choices=PERIODICITY_CHOICES,
        default='once',
        verbose_name='Периодичность'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created', verbose_name='Статус')
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='mailings', verbose_name='Сообщение')
    recipients = models.ManyToManyField(Recipient, related_name='mailings', verbose_name='Получатели')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mailings',
        verbose_name='Владелец',
        null=True
    )

    class Meta:
        verbose_name = 'Рассылка'
        verbose_name_plural = 'Рассылки'
        permissions = [
            ('can_view_all_mailings', 'Может просматривать все рассылки'),
            ('can_change_any_mailing', 'Может редактировать любые рассылки'),
            ('can_delete_any_mailing', 'Может удалять любые рассылки'),
        ]

    def __str__(self):
        return f'Рассылка от {self.start_time.strftime("%d.%m.%Y %H:%M")}'

    def update_status(self):
        """Обновляет статус рассылки на основе текущего времени"""
        now = timezone.now()
        new_status = self.status

        if now < self.start_time:
            new_status = 'created'
        elif self.start_time <= now <= self.end_time:
            new_status = 'started'
        elif now > self.end_time:
            new_status = 'completed'

        if new_status != self.status:
            self.status = new_status
            self.save(update_fields=['status'])

    def clean(self):
        """Валидация дат"""
        if self.start_time and self.start_time < timezone.now():
            raise ValidationError('Дата начала не может быть в прошлом')

        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError('Дата начала должна быть раньше даты окончания')

    def save(self, *args, **kwargs):
        self.full_clean()  # Вызываем валидацию перед сохранением
        super().save(*args, **kwargs)


class MailingAttempt(models.Model):
    """Модель попытки отправки рассылки"""
    STATUS_CHOICES = [
        ('success', 'Успешно'),
        ('failed', 'Не успешно'),
    ]

    attempt_time = models.DateTimeField(auto_now_add=True, verbose_name='Дата и время попытки')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name='Статус')
    server_response = models.TextField(blank=True, null=True, verbose_name='Ответ почтового сервера')
    related_mailing = models.ForeignKey(
        'Mailing',
        on_delete=models.CASCADE,
        related_name='attempts',
        verbose_name='Рассылка'
    )

    class Meta:
        verbose_name = 'Попытка рассылки'
        verbose_name_plural = 'Попытки рассылок'
        ordering = ['-attempt_time']

    def __str__(self):
        return f'Попытка {self.get_status_display()} от {self.attempt_time}'
