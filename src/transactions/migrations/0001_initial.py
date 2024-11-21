# Generated by Django 5.1.3 on 2024-11-21 05:02

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Basename',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Добавлено')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
                ('basename', models.CharField(max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='LinkedUserToBasename',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='Summary',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Добавлено')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
                ('period_month', models.IntegerField()),
                ('period_year', models.IntegerField()),
                ('type_transaction', models.CharField(choices=[('income', 'Income'), ('expense', 'Expense')], max_length=10)),
                ('group_name', models.CharField(max_length=30)),
                ('plan_value', models.DecimalField(decimal_places=2, max_digits=12)),
                ('fact_value', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
            ],
            options={
                'verbose_name': 'свод',
                'verbose_name_plural': 'своды',
                'ordering': ('-updated_at', '-created_at'),
                'default_related_name': 'summaries',
            },
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Добавлено')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
                ('period_month', models.IntegerField()),
                ('period_year', models.IntegerField()),
                ('group_name', models.CharField(max_length=30)),
                ('description', models.TextField(blank=True)),
                ('type_transaction', models.CharField(choices=[('income', 'Income'), ('expense', 'Expense')], max_length=10)),
                ('value_transaction', models.DecimalField(decimal_places=2, max_digits=12)),
            ],
            options={
                'verbose_name': 'транзакция',
                'verbose_name_plural': 'транзакции',
                'ordering': ('-updated_at', '-created_at'),
                'default_related_name': 'transactions',
            },
        ),
    ]
