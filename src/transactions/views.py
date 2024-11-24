from datetime import datetime

from django.contrib.auth import authenticate, login
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.generic import TemplateView

from transactions.forms import RegistrationForm
from transactions.models import Summary, Basename
from users.models import TelegramSettings, CoreSettings


class HomePageView(TemplateView):
    template_name = 'transactions/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'FF'
        return context


class SummaryView(TemplateView):
    template_name = 'transactions/summary.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        summary = Summary.objects.filter(
            period_month=self.request.user.core_settings.current_month,
            period_year=self.request.user.core_settings.current_year,
            basename=self.request.user.core_settings.current_basename
        )
        context['title'] = 'FF'
        context['income'] = summary.filter(
            type_transaction='income'
        )
        context['expense'] = summary.filter(
            type_transaction='expense'
        )
        return context


def login_ajax(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse(
                {
                    'status': 'error',
                    'message': 'Неправильное имя пользователя или пароль'}
            )
    return JsonResponse(
        {'status': 'error', 'message': 'Некорректный запрос'}
    )

def registration(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password'])
                user.save()
                TelegramSettings.objects.create(
                    user=user,
                    telegram_only=False
                )
                basename = Basename.objects.create(
                    user=user,
                    basename=user.username
                )
                dt = datetime.now()
                CoreSettings.objects.create(
                    user=user,
                    current_basename=basename,
                    current_month=dt.month,
                    current_year=dt.year
                )
            return JsonResponse(
                {'status': 'success'}
            )
        else:
            return JsonResponse(
                {
                    'status': 'error',
                    'message': list(form.errors.values())
                }
            )
    return JsonResponse(
        {'status': 'error', 'message': 'Некорректный запрос'}
    )
