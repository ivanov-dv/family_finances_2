from django import forms
from django.conf import settings

from .models import User


class RegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        label='Пароль'
    )

    class Meta:
        model = User
        fields = ('username', 'password')

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(
                f'Логин {username} уже занят'
            )
        if username in settings.NOT_ALLOWED_USERNAMES:
            raise forms.ValidationError(
                f'Логин {username} зарезервирован'
            )
        return username
