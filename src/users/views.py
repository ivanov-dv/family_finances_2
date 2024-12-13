from datetime import datetime

from django.conf import settings
from django.contrib.auth import authenticate, login, get_user_model
from django.db import transaction
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django_telegram_login.authentication import verify_telegram_authentication
from django_telegram_login.errors import (
    TelegramDataIsOutdatedError,
    NotTelegramDataError
)

from transactions.models import Space
from .forms import RegistrationForm
from .models import TelegramSettings, CoreSettings

User = get_user_model()


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
        basename = Space.objects.create(
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


def telegram_auth(request):
    if not request.GET.get('hash'):
        return HttpResponse(
            'Handle the missing Telegram data in the response.'
        )
    try:
        verify_data = verify_telegram_authentication(
            bot_token=settings.BOT_TOKEN, request_data=request.GET
        )
        auth_user = authenticate(
            request,
            username=verify_data['id'],
            password=settings.AUTH_TOKEN
        )
        if not auth_user:
            new_user = User.objects.create(
                username=verify_data['id'],
                first_name=verify_data['first_name'],
                last_name=verify_data['last_name']
            )
            new_user.set_password('test')
            auth_user_after_create_account = authenticate(
                request,
                username=verify_data['id'],
                password='test'
            )
            login(request, auth_user_after_create_account)
        else:
            login(request, auth_user)
    except TelegramDataIsOutdatedError as _ex1:
        return HttpResponse('Authentication was received more than a day ago.')
    except NotTelegramDataError as _ex2:
        return HttpResponse('The data is not related to Telegram!')
    except Exception as _ex3:
        return HttpResponse(f"Ошибка {_ex3.__class__.__name__}: {_ex3}")
    return HttpResponseRedirect(reverse('transactions:home'))
