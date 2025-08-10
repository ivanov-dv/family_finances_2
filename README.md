![Tests](https://github.com/ivanov-dv/family_finances_2/actions/workflows/main.yml/badge.svg)

# Django сервис для ведения семейного бюджета на базе Django + Rest Framework.

### Описание:
- ведение учета доходов и расходов пользователей по месяцам;
- веб-интерфейс позволяет частично просмотреть отчеты по периодам (в процессе разработки);
- взаимодействие с пользователем осуществляется через [телеграм сервис](https://github.com/ivanov-dv/ff2_telegram_ui), который взаимодействует с данным сервисом через API;
- возможна выгрузка операций в excel;
- доступна авторизация через Telegram ID;
- поддерживается взаимодействие через Telegram WebApp.

### Применяемые библиотеки и технологии:
- Python 3.12;
- Django + DRF;
- PostgreSQL;
- Pytest;
- Poetry;
- Nginx;
- Docker;
- Kubernetes;
- CI/CD.

### Запуск приложения в Docker:
1. Клонируйте репозиторий `git clone https://github.com/ivanov-dv/family_finances_2.git`.
2. Перейдите в папку репозитория `cd family_finances_2`.
3. Запустите приложение с помощью Docker Compose. 
Из корневой папки репозитория выполните команду `docker compose -f docker-compose.dev.yml up -d`
4. Сервис доступен по адресу `localhost:9000/api/v1/`
5. Динамическая документация: `localhost:9000/redoc/` и 
`localhost:9000/swagger/`

P.S. В БД будут автоматически добавлены демонстрационные записи.

### Запуск Django приложения без Docker:
1. Клонируйте репозиторий `git clone https://github.com/ivanov-dv/family_finances_2.git`.
2. Перейдите в папку репозитория `cd family_finances_2`.
3. Установите [poetry](https://python-poetry.org/docs/).
4. Установите зависимости `poetry install --with dev`.
5. Создайте и заполните `.env` по примеру `.env.example`. При отсутствии PostgreSQL используйте `USE_SQLITE=true`.
6. Перейдите в папку src `cd src`.
7. Примените миграции `python manage.py migrate`.
8. Запустите приложение (можно указать любой доступный порт) `python manage.py runserver 0.0.0.0:8888`.

#### Также можете использовать приложение, развернутое на моем сервере https://t.me/family_finance_2_bot