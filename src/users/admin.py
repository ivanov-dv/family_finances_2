from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

from .models import User


class SiteUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User


class SiteUserCreationForm(AdminUserCreationForm):
    class Meta(AdminUserCreationForm.Meta):
        model = User


@admin.register(User)
class SiteUserAdmin(UserAdmin):
    """Пользователи сервиса. Регистрация через сайт создаёт неактивного пользователя —
    подтверждается здесь действием «Подтвердить регистрацию»."""

    form = SiteUserChangeForm
    add_form = SiteUserCreationForm
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_active', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'is_superuser')
    actions = ('activate_users',)

    @admin.action(description='Подтвердить регистрацию (активировать выбранных)')
    def activate_users(self, request, queryset):
        updated = queryset.filter(is_active=False).update(is_active=True)
        self.message_user(request, f'Подтверждено пользователей: {updated}', messages.SUCCESS)
