from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView, LogoutView
from django.core.mail import send_mail
from django.conf import settings
from .forms import UserRegistrationForm, UserLoginForm
from .models import User


class UserRegistrationView(CreateView):
    model = User
    form_class = UserRegistrationForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('mail:home')

    def form_valid(self, form):
        response = super().form_valid(form)

        # Отправка приветственного письма
        send_mail(
            subject='Добро пожаловать!',
            message=f'Здравствуйте, {self.object.email}!\n\n'
                    f'Вы успешно зарегистрировались на нашем сайте.',
            from_email=settings.DEFAULT_FROM_EMAIL or 'noreply@example.com',
            recipient_list=[self.object.email],
            fail_silently=True,
        )

        # Автоматический вход после регистрации
        login(self.request, self.object)
        messages.success(self.request, 'Регистрация прошла успешно!')
        return response


class UserLoginView(LoginView):
    form_class = UserLoginForm
    template_name = 'users/login.html'
    next_page = reverse_lazy('mail:home')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'С возвращением, {self.request.user.email}!')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Неверный email или пароль')
        return super().form_invalid(form)


class UserLogoutView(LogoutView):
    """Выход из системы"""
    next_page = reverse_lazy('mail:home')

    def dispatch(self, request, *args, **kwargs):
        messages.info(request, 'Вы вышли из системы')
        return super().dispatch(request, *args, **kwargs)
