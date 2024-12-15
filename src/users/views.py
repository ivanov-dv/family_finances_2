import hashlib
import hmac
from datetime import datetime
from operator import itemgetter
from pprint import pprint
from urllib.parse import parse_qsl

from django.conf import settings
from django.contrib.auth import authenticate, login, get_user_model
from django.db import transaction
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
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
        space = Space.objects.create(
            user=user,
            name=user.username
        )
        dt = datetime.now()
        CoreSettings.objects.create(
            user=user,
            current_space=space,
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
        user = User.objects.filter(username=verify_data['id']).first()
        if not user:
            with transaction.atomic():
                new_user = User.objects.create(
                    username=verify_data['id'],
                    first_name=verify_data['first_name'],
                    last_name=verify_data['last_name']
                )
                new_user.set_password(
                    str(verify_data['id']) + settings.SECRET_KEY
                )
                new_user.save()
                TelegramSettings.objects.create(
                    user=new_user,
                    telegram_only=True,
                    id_telegram=verify_data['id']
                )
                space = Space.objects.create(
                    user=new_user,
                    name=new_user.username
                )
                dt = datetime.now()
                CoreSettings.objects.create(
                    user=new_user,
                    current_space=space,
                    current_month=dt.month,
                    current_year=dt.year
                )
            login(request, new_user)
        else:
            login(request, user)
    except TelegramDataIsOutdatedError:
        return HttpResponse('Authentication was received more than a day ago.')
    except NotTelegramDataError:
        return HttpResponse('The data is not related to Telegram!')
    except Exception as _ex3:
        return HttpResponse(f"Ошибка {_ex3.__class__.__name__}: {_ex3}")
    return HttpResponseRedirect(reverse('transactions:home'))


def check_telegram_auth(init_data: str, token: str) -> bool:
    """Проверка подлинности данных Telegram Web App."""
    try:
        parsed_data = dict(parse_qsl(init_data))
    except ValueError:
        # Init data is not a valid query string
        return False
    if "hash" not in parsed_data:
        # Hash is not present in init data
        return False

    hash_ = parsed_data.pop('hash')
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed_data.items(), key=itemgetter(0))
    )
    secret_key = hmac.new(
        key=b"WebAppData", msg=token.encode(), digestmod=hashlib.sha256
    )
    calculated_hash = hmac.new(
        key=secret_key.digest(), msg=data_check_string.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()
    return calculated_hash == hash_


def webapp(request):
    if request.method == 'GET':
        return render(request, 'webapp/webapp.html')


def webapp_auth(request):
    if request.method == "POST":
        import json
        data = json.loads(request.body)
        pprint(data)

        init_data = data.get("initData")
        if not check_telegram_auth(init_data, settings.BOT_TOKEN):
            return JsonResponse(
                {"success": False, "error": "Invalid Telegram data"})

        # Получаем ID пользователя Telegram
        user_id = init_data.split("id=")[1].split("&")[0]
        # username = init_data.split("username=")[1].split("&")[0]

        # Создаем пользователя, если его еще нет
        user, created = User.objects.get_or_create(
            telegram_settings__id_telegram=user_id,
            defaults={
                "password": str(user_id) + settings.SECRET_KEY,
                "telegram_only": True,
                "id_telegram": user_id
            })

        # Выполняем автоматический логин
        login(request, user)
        return JsonResponse({"success": True})

    return JsonResponse({"success": False, "error": "Invalid request method"})
