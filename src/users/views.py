from datetime import datetime

from django.contrib.auth import authenticate, login
from django.db import transaction
from django.http import JsonResponse

from .forms import RegistrationForm
from .models import TelegramSettings, CoreSettings
from transactions.models import Basename


def login_ajax(request):
    if not request.method == 'POST':
        return JsonResponse(
            {'status': 'error', 'message': 'Некорректный запрос'}
        )
    username = request.POST.get('username')
    password = request.POST.get('password')
    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse(
            {
                'status': 'error',
                'message': 'Неправильное имя пользователя или пароль'}
        )
    login(request, user)
    return JsonResponse({'status': 'success'})


def registration(request):
    if not request.method == 'POST':
        return JsonResponse(
            {'status': 'error', 'message': 'Некорректный запрос'}
        )
    form = RegistrationForm(request.POST)
    if not form.is_valid():
        return JsonResponse(
            {
                'status': 'error',
                'message': list(form.errors.values())
            }
        )
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
