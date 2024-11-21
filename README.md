# API сервис для ведения семейного бюджета на базе Django Rest Framework.

### Описание:
- Предназначен для взаимодействия с телеграм интерфейсом 
и учета операций пользователей;
- Не предназначен для прямого взаимодействия с пользователями;
- В перспективе планируется: 
  1. реализация выгрузки операций в файл (excel, csv);
  2. внедрение веб-интерфейса через Django.

### Применяемые библиотеки и технологии:
- Django REST Framework;
- Pytest;
- Poetry;
- Docker Compose.

### Запуск:
1. Клонируйте репозиторий.
2. Запустите приложение с помощью Docker Compose. 
Из корневой папки репозитория выполните команду `docker compose up --build`
3. Сервис доступен по адресу `localhost:8000/api/v1/`
4. Динамическая документация: `localhost:8000/redoc/` и `localhost:8000/swagger/`