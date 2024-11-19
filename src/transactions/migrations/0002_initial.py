# Generated by Django 5.1.3 on 2024-11-19 13:48

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('transactions', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='basename',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='summary',
            name='basename',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='transactions.basename'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='author',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='transaction',
            name='basename',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='transactions.basename'),
        ),
        migrations.AddConstraint(
            model_name='basename',
            constraint=models.UniqueConstraint(fields=('user', 'basename'), name='unique_basename_user'),
        ),
    ]
