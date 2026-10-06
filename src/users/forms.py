from django import forms
from django.conf import settings
from django.contrib.auth.password_validation import validate_password

from .models import User


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name')
        labels = {
            'email': 'Email',
            'first_name': 'Имя',
            'last_name': 'Фамилия',
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            return email
        qs = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                'Этот email уже используется другим пользователем'
            )
        return email


class RegistrationForm(forms.ModelForm):
    # strip=False: пробелы в пароле значимы, а при входе пароль не обрезается.
    password = forms.CharField(
        widget=forms.PasswordInput,
        label='Пароль',
        strip=False
    )

    class Meta:
        model = User
        fields = ('username', 'password')

    def clean_username(self):
        # Логины хранятся в нижнем регистре (User.save), поэтому и проверяем в нём:
        # иначе «Admin» обходит список зарезервированных, а «Ivan» при «ivan» даёт 500.
        username = self.cleaned_data['username'].strip().lower()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(
                f'Логин {username} уже занят'
            )
        if username in settings.NOT_ALLOWED_USERNAMES:
            raise forms.ValidationError(
                f'Логин {username} зарезервирован'
            )
        if username[0].isdigit():
            raise forms.ValidationError('Логин не может начинаться с цифры')
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        if password:
            try:
                validate_password(
                    password, user=User(username=cleaned_data.get('username', ''))
                )
            except forms.ValidationError as error:
                self.add_error('password', error)
        return cleaned_data
