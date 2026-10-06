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
7. Примените миграции `poetry run python manage.py migrate`.
8. Запустите приложение (можно указать любой доступный порт) `poetry run python manage.py runserver 0.0.0.0:8888`.

### Деплой в Kubernetes (k0s) вручную, без GitHub Actions:
Скрипт `scripts/deploy.sh` повторяет job `deploy_via_k8s` из `.github/workflows/main.yml`: собирает образ из последнего коммита, 
публикует его в Docker Hub, выполняет миграции и `collectstatic` (Job `django-collectstatic`), 
затем перезапускает `ff2-django` и `ff2-nginx`. Локальный `kubectl` и kubeconfig не нужны: скрипт подключается к серверу 
по SSH и выполняет там `k0s kubectl`.

Что нужно:
1. SSH-доступ к серверу (`ssh пользователь@сервер`) и право выполнять `sudo k0s kubectl` без пароля (или вход под root). 
Проверка: `ssh пользователь@сервер 'sudo k0s kubectl get nodes'`.
2. Вход в Docker Hub там, где собирается образ (`docker login`; образ публикуется как `ivanovdv/ff2-django`). 
Если архитектура вашей машины совпадает с серверной (или стоит `docker buildx`), образ собирается у вас, иначе — на сервере: 
там должен быть Docker и выполнен `docker login` (или задайте `DOCKER_USERNAME` и `DOCKER_PASSWORD`).
3. Секрет `ff2-django-env` в кластере (он уже есть, раз сайт работает).

Запуск из корня репозитория на нужном коммите (обычно `main` после слияния):
```
scripts/deploy.sh --ssh пользователь@сервер --dry-run   # показать план, ничего не меняя
scripts/deploy.sh --ssh пользователь@сервер             # выкатить (спросит подтверждение)
```
Адрес можно не повторять: `export DEPLOY_SSH=пользователь@сервер`. Если скрипт запущен прямо на сервере — 
`scripts/deploy.sh --kubectl "sudo k0s kubectl"`; при обычном локальном `kubectl` — просто `scripts/deploy.sh`.

Деплоится последний коммит (`git archive HEAD`), а не рабочее дерево. Миграции выполняются до перезапуска приложения: 
если Job упал, прежняя версия продолжает работать.

Откат: каждый образ публикуется и с тегом SHA коммита, поэтому вернуться на предыдущую версию можно командой 
`scripts/deploy.sh --ssh пользователь@сервер --skip-build --tag <sha>` (откат миграций БД скрипт не делает). 
Все параметры: `scripts/deploy.sh --help`.

#### Также можете использовать приложение, развернутое на моем сервере https://t.me/family_finance_2_bot