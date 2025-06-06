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

### Запуск:
1. Клонируйте репозиторий.
2. Запустите приложение с помощью Docker Compose. 
Из корневой папки репозитория выполните команду `docker compose -f docker-compose.dev.yml up -d`
3. Сервис доступен по адресу `localhost:9000/api/v1/`
4. Динамическая документация: `localhost:9000/redoc/` и 
`localhost:9000/swagger/`

P.S. В БД будут автоматически добавлены демонстрационные записи.
