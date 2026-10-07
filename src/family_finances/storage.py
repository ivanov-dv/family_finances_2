import hashlib
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles.storage import StaticFilesStorage

# Файлы с неизменным путём: версия или начертание уже в имени (vendor/bootstrap/5.3.3/…, fonts/inter-…-400-normal.woff2).
# Им «?v=» не нужен, а для шрифтов он бы разошёлся с url() в fonts.css и сломал бы preload.
UNVERSIONED_PREFIXES = ('fonts/', 'vendor/')


@lru_cache(maxsize=512)
def _content_version(path: str, mtime_ns: int) -> str:
    """Короткий хеш содержимого; mtime — только ключ кеша, чтобы правка файла сразу меняла версию."""
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()[:10]


class VersionedStaticFilesStorage(StaticFilesStorage):
    """Добавляет к URL собственной статики проекта (src/static) ?v=<хеш содержимого>.

    Без версии браузер держит старые JS/CSS по эвристике (nginx отдаёт их без Cache-Control), и после выкладки
    часть пользователей работает со старым скриптом при новой вёрстке. С версией nginx кеширует такие URL на год
    (map $arg_v в конфигурации), а любая правка файла меняет адрес. Статика библиотек (admin, DRF и т. п.) не
    затрагивается: её нет в src/static.
    """

    def url(self, name):
        url = super().url(name)
        if name.startswith(UNVERSIONED_PREFIXES):
            return url
        path = Path(settings.BASE_DIR) / 'static' / name
        try:
            mtime_ns = path.stat().st_mtime_ns
        except OSError:
            return url
        separator = '&' if '?' in url else '?'
        return f'{url}{separator}v={_content_version(str(path), mtime_ns)}'
