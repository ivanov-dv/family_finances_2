# Generated by Django 5.1.4 on 2024-12-17 11:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_remove_telegramsettings_joint_chat'),
    ]

    operations = [
        migrations.AlterField(
            model_name='telegramsettings',
            name='id_telegram',
            field=models.BigIntegerField(blank=True, default=None, null=True, unique=True),
        ),
    ]
