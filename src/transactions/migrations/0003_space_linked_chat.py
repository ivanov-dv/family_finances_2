# Generated by Django 5.1.4 on 2024-12-17 10:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='space',
            name='linked_chat',
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
    ]
