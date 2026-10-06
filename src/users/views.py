import hashlib
import hmac
from datetime import datetime
from operator import itemgetter
from urllib.parse import parse_qsl

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError, transaction
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import UpdateView
from django_telegram_login.authentication import verify_telegram_authentication
from django_telegram_login.errors import (
    TelegramDataIsOutdatedError,
    NotTelegramDataError
)

from transactions.models import Space
from transactions.services import SpaceService
from transactions.views import get_safe_next_url
from .forms import ProfileForm, RegistrationForm
from .models import TelegramSettings, CoreSettings

User = get_user_model()


class LoginPageView(auth_views.LoginView):
    """Страница, на которую login_required отправляет анонима; вошедшего уводит дальше."""

    redirect_authenticated_user = True

    def get_redirect_url(self):
        url = super().get_redirect_url()
        # next на саму страницу входа дал бы для вошедшего ValueError («петля редиректов»).
        return '' if url == self.request.path else url


def login_ajax(request):
    if not request.method == 'POST':
        return JsonResponse(
            {'status': 'error', 'message': 'Некорректный запрос'}
        )
    # Логины хранятся в нижнем регистре, а на телефонах первая буква часто вводится заглавной.
    username = (request.POST.get('username') or '').strip().lower()
    password = request.POST.get('password') or ''
    wrong = JsonResponse(
        {
            'status': 'error',
            'message': 'Неправильное имя пользователя или пароль'}
    )
    # NUL в значении роняет запрос к PostgreSQL (500).
    if not username or not password or '\x00' in username:
        return wrong
    user = authenticate(request, username=username, password=password)
    if user is None:
        # authenticate() не пускает неактивных: подсказываем про подтверждение,
        # но только тому, кто знает пароль (иначе можно перебирать логины).
        pending = User.objects.filter(username=username, is_active=False).first()
        if pending and pending.check_password(password):
            return JsonResponse(
                {
                    'status': 'error',
                    'message': 'Аккаунт ещё не подтверждён администратором'}
            )
        return wrong
    login(request, user)
    return JsonResponse({'status': 'success', 'next': get_safe_next_url(request)})


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
                'message': [
                    str(message)
                    for errors in form.errors.values()
                    for message in errors
                ]
            }
        )
    try:
        with transaction.atomic():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.is_active = False
            user.save()
            TelegramSettings.objects.create(
                user=user,
                telegram_only=False
            )
            space = Space.objects.create(
                user=user,
                name=SpaceService.default_name(user.username)
            )
            now = timezone.localtime()
            CoreSettings.objects.create(
                user=user,
                current_space=space,
                current_month=now.month,
                current_year=now.year
            )
    except IntegrityError:
        # Две одинаковые регистрации одновременно: форма дубль не увидела, поймала БД.
        return JsonResponse(
            {'status': 'error', 'message': ['Этот логин уже занят']}
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
        return False
    if 'hash' not in parsed_data:
        return False

    hash_ = parsed_data.pop('hash')
    data_check_string = '\n'.join(
        f'{k}={v}' for k, v in sorted(parsed_data.items(), key=itemgetter(0))
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


@csrf_exempt
def webapp_auth(request):
    if request.method == 'POST':
        import json
        data = json.loads(request.body)

        init_data = data.get('initData')
        if not check_telegram_auth(init_data, settings.BOT_TOKEN):
            return JsonResponse(
                {'success': False, 'error': 'Invalid Telegram data'}
            )

        from urllib.parse import parse_qs
        parsed_data = parse_qs(init_data)
        user_data = parsed_data.get('user', [None])[0]
        parsed_user = json.loads(user_data)
        user_id = parsed_user.get('id', None)
        user = User.objects.filter(
            telegram_settings__id_telegram=user_id,
        ).first()
        if not user:
            user = User.objects.create(username=user_id)
            user.set_password(str(user_id) + settings.SECRET_KEY)
            user.save()
            TelegramSettings.objects.create(
                user=user,
                telegram_only=True,
                id_telegram=user_id
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
        login(request, user)
        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})


class ProfileView(LoginRequiredMixin, UpdateView):
    # По умолчанию UpdateView кладёт объект в контекст как «user» и перекрывает им
    # request.user из шаблонов (шапка, сайдбар).
    context_object_name = 'profile_user'
    form_class = ProfileForm
    template_name = 'users/profile.html'
    success_url = reverse_lazy('users:profile')

    def get_object(self, queryset=None):
        # Копия, а не request.user: ModelForm меняет instance при валидации, и при ошибке
        # в форме шапка показывала бы несохранённое имя.
        return User.objects.get(pk=self.request.user.pk)

    def form_valid(self, form):
        messages.success(self.request, 'Профиль обновлён')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        core_settings = CoreSettings.objects.filter(user=user).first()
        telegram_settings = TelegramSettings.objects.filter(user=user).first()
        owned_spaces = (
            Space.objects
            .filter(user=user)
            .prefetch_related('linkedusertospace_set__linked_user')
            .order_by('name')
        )
        context.update({
            'title': settings.PROJECT_TITLE,
            'current_space': core_settings.current_space if core_settings else None,
            'current_month': core_settings.current_month if core_settings else None,
            'current_year': core_settings.current_year if core_settings else None,
            'telegram_settings': telegram_settings,
            'owned_spaces': owned_spaces,
            'owned_count': len(owned_spaces),
            'next': self.request.path,
        })
        return context


class PasswordChangeView(LoginRequiredMixin, auth_views.PasswordChangeView):
    template_name = 'users/password_change.html'
    success_url = reverse_lazy('users:profile')

    def form_valid(self, form):
        messages.success(self.request, 'Пароль успешно изменён')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        core_settings = CoreSettings.objects.filter(user=user).first()
        context.update({
            'title': settings.PROJECT_TITLE,
            'current_space': core_settings.current_space if core_settings else None,
            'current_month': core_settings.current_month if core_settings else None,
            'current_year': core_settings.current_year if core_settings else None,
            'next': self.request.path,
        })
        return context
