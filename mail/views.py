from django.shortcuts import render
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy
from .models import Mailing, Recipient, Message, MailingAttempt
from .services import MailingService
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth import get_user_model
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.core.cache import cache
from django.views.decorators.vary import vary_on_cookie

User = get_user_model()


class MailingSendView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'mail.change_mailing'

    def has_permission(self):
        mailing = get_object_or_404(Mailing, pk=self.kwargs['pk'])
        return super().has_permission() or self.request.user == mailing.owner

    def post(self, request, pk):
        mailing = get_object_or_404(Mailing, pk=pk)
        try:
            results = MailingService.send_mailing(mailing)
            success = sum(1 for r in results if r['success'])
            failed = len(results) - success
            messages.success(request, f'Отправлено. Успешно: {success}, Ошибок: {failed}')
        except Exception as e:
            messages.error(request, str(e))
        return redirect('mail:mailing_detail', pk=pk)


@method_decorator(cache_page(60 * 5), name='dispatch')
class RecipientListView(LoginRequiredMixin, ListView):
    model = Recipient
    template_name = 'mail/recipient_list.html'
    context_object_name = 'recipients'

    def get_queryset(self):
        # Кеширование queryset на 5 минут
        cache_key = f'recipient_list_{self.request.user.id}_{self.request.user.has_perm("mail.view_recipient")}'
        queryset = cache.get(cache_key)

        if not queryset:
            if self.request.user.has_perm('mail.view_recipient'):
                queryset = Recipient.objects.all()
            else:
                queryset = Recipient.objects.filter(owner=self.request.user)
            cache.set(cache_key, queryset, 300)  # 5 минут

        return queryset


@method_decorator(cache_page(60 * 15), name='dispatch')
@method_decorator(vary_on_cookie, name='dispatch')
class RecipientDetailView(LoginRequiredMixin, DetailView):
    model = Recipient
    template_name = 'mail/recipient_detail.html'
    context_object_name = 'recipient'

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not (request.user == obj.owner or request.user.has_perm('mail.view_recipient')):
            messages.error(request, 'У вас нет прав для просмотра')
            return redirect('mail:recipient_list')
        return super().dispatch(request, *args, **kwargs)


class RecipientCreateView(LoginRequiredMixin, CreateView):
    model = Recipient
    fields = ['email', 'full_name', 'comment']
    template_name = 'mail/recipient_form.html'
    success_url = reverse_lazy('mail:recipient_list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        cache.delete('home_stats')
        cache.delete(f'recipient_list_{self.request.user.id}_False')
        return super().form_valid(form)


class RecipientUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Recipient
    fields = ['email', 'full_name', 'comment']
    template_name = 'mail/recipient_form.html'
    success_url = reverse_lazy('mail:recipient_list')
    permission_required = 'mail.change_recipient'

    def has_permission(self):
        obj = self.get_object()
        return super().has_permission() or self.request.user == obj.owner

    def form_valid(self, form):
        # Сброс кеша
        cache.delete('home_stats')
        cache.delete(f'recipient_list_{self.request.user.id}_False')
        cache.delete(f'recipient_detail_{self.object.pk}')


class RecipientDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Recipient
    template_name = 'mail/recipient_confirm_delete.html'
    success_url = reverse_lazy('mail:recipient_list')
    context_object_name = 'recipient'
    permission_required = 'mail.delete_recipient'

    def has_permission(self):
        obj = self.get_object()
        return super().has_permission() or self.request.user == obj.owner

    def delete(self, request, *args, **kwargs):
        # Сброс кеша
        cache.delete('home_stats')
        cache.delete(f'recipient_list_{self.request.user.id}_False')

        return super().delete(request, *args, **kwargs)


@method_decorator(cache_page(60 * 5), name='dispatch')
class MessageListView(ListView):
    model = Message
    template_name = 'mail/message_list.html'
    context_object_name = 'messages'

    def get_queryset(self):
        cache_key = 'message_list'
        queryset = cache.get(cache_key)

        if not queryset:
            queryset = Message.objects.all()
            cache.set(cache_key, queryset, 300)  # 5 минут

        return queryset


@method_decorator(cache_page(60 * 15), name='dispatch')
@method_decorator(vary_on_cookie, name='dispatch')
class MessageDetailView(DetailView):
    model = Message
    template_name = 'mail/message_detail.html'
    context_object_name = 'message'


class MessageCreateView(CreateView):
    model = Message
    fields = ['subject', 'body']
    template_name = 'mail/message_form.html'
    success_url = reverse_lazy('mail:message_list')


class MessageUpdateView(UpdateView):
    model = Message
    fields = ['subject', 'body']
    template_name = 'mail/message_form.html'
    success_url = reverse_lazy('mail:message_list')


class MessageDeleteView(DeleteView):
    model = Message
    template_name = 'mail/message_confirm_delete.html'
    success_url = reverse_lazy('mail:message_list')
    context_object_name = 'message'


@method_decorator(cache_page(60 * 5), name='dispatch')
class MailingListView(LoginRequiredMixin, ListView):
    model = Mailing
    template_name = 'mail/mailing_list.html'
    context_object_name = 'mailings'

    def get_queryset(self):
        cache_key = f'mailing_list_{self.request.user.id}_{self.request.user.has_perm("mail.view_mailing")}'
        queryset = cache.get(cache_key)

        if not queryset:
            if self.request.user.has_perm('mail.view_mailing'):
                queryset = Mailing.objects.all()
            else:
                queryset = Mailing.objects.filter(owner=self.request.user)
            cache.set(cache_key, queryset, 300)  # 5 минут

        return queryset


@method_decorator(cache_page(60 * 15), name='dispatch')
@method_decorator(vary_on_cookie, name='dispatch')
class MailingDetailView(LoginRequiredMixin, DetailView):
    model = Mailing
    template_name = 'mail/mailing_detail.html'
    context_object_name = 'mailing'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        obj.update_status()
        return obj

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not (request.user == obj.owner or request.user.has_perm('mail.view_mailing')):
            messages.error(request, 'У вас нет прав для просмотра этой рассылки')
            return redirect('mail:mailing_list')
        return super().dispatch(request, *args, **kwargs)


class MailingCreateView(LoginRequiredMixin, CreateView):
    model = Mailing
    fields = ['start_time', 'end_time', 'message', 'recipients']
    template_name = 'mail/mailing_form.html'
    success_url = reverse_lazy('mail:mailing_list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class MailingUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Mailing
    fields = ['start_time', 'end_time', 'message', 'recipients']
    template_name = 'mail/mailing_form.html'
    success_url = reverse_lazy('mail:mailing_list')
    permission_required = 'mail.change_mailing'

    def has_permission(self):
        obj = self.get_object()
        return super().has_permission() or self.request.user == obj.owner


class MailingDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Mailing
    template_name = 'mail/mailing_confirm_delete.html'
    success_url = reverse_lazy('mail:mailing_list')
    context_object_name = 'mailing'
    permission_required = 'mail.delete_mailing'

    def has_permission(self):
        obj = self.get_object()
        return super().has_permission() or self.request.user == obj.owner


class HomeView(TemplateView):
    template_name = 'mail/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Кеширование общей статистики на 5 минут
        cache_key = 'home_stats'
        stats = cache.get(cache_key)

        if not stats:
            stats = {
                'total_mailings': Mailing.objects.count(),
                'active_mailings': MailingService.get_active_count(),
                'total_recipients': Recipient.objects.count(),
            }
            cache.set(cache_key, stats, 300)

        context['total_mailings'] = stats['total_mailings']
        context['active_mailings'] = stats['active_mailings']
        context['total_recipients'] = stats['total_recipients']

        # Статистика пользователя (не кешируется - персональная)
        if self.request.user.is_authenticated:
            user_mailings = Mailing.objects.filter(owner=self.request.user)
            user_attempts = MailingAttempt.objects.filter(related_mailing__in=user_mailings)

            context['user_total_attempts'] = user_attempts.count()
            context['user_successful_attempts'] = user_attempts.filter(status='success').count()
            context['user_failed_attempts'] = user_attempts.filter(status='failed').count()
            context['user_sent_messages'] = user_attempts.filter(status='success').count()
        else:
            context['user_total_attempts'] = 0
            context['user_successful_attempts'] = 0
            context['user_failed_attempts'] = 0
            context['user_sent_messages'] = 0

        return context


class UserListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = User
    template_name = 'mail/user_list.html'
    context_object_name = 'users'
    permission_required = 'auth.view_user'


class UserBlockView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'auth.change_user'

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        user.is_active = not user.is_active
        user.save()
        action = "разблокирован" if user.is_active else "заблокирован"
        messages.success(request, f'Пользователь {user.email} {action}')
        return redirect('mail:user_list')
