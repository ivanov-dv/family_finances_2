"""Статика: собственные библиотеки и шрифты вместо CDN, версионные URL, согласованность конфигов nginx.

Страницы не должны зависеть от чужих хостов: с них шрифты догружались уже после первой отрисовки (текст менял вид
через секунду после перехода), а зависший CDN задерживал и сам дашборд.
"""
import hashlib
import os
import re
from pathlib import Path

import pytest
import yaml
from django.conf import settings
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.test import override_settings
from django.urls import reverse

from family_finances.storage import UNVERSIONED_PREFIXES, VersionedStaticFilesStorage

pytestmark = pytest.mark.django_db(transaction=True)

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(settings.BASE_DIR) / 'static'
EXTERNAL_URL = re.compile(r'''(?:src|href|action)=["'](https?://[^"']+)["']''')
STATIC_URL = re.compile(r'''(?:src|href)=["'](/static/[^"']+)["']''')

APP_PAGES = ('transactions:summary', 'transactions:transactions', 'transactions:add_summary',
             'transactions:add_transaction', 'transactions:change_period', 'users:profile')


def page(client, name):
    resp = client.get(reverse(name))
    assert resp.status_code == 200, name
    return resp.content.decode()


def without_scripts(html):
    return re.sub(r'<script.*?</script>', '', html, flags=re.S)


class TestNoThirdPartyHosts:

    @pytest.mark.parametrize('name', APP_PAGES)
    def test_app_pages_load_everything_from_own_host(self, user_1_client, name):
        assert EXTERNAL_URL.findall(page(user_1_client, name)) == []

    def test_guest_page_talks_only_to_telegram(self, client):
        hosts = {re.sub(r'^https?://([^/]+).*$', r'\1', u) for u in EXTERNAL_URL.findall(client.get('/').content.decode())}
        assert hosts <= {'telegram.org'}

    def test_bootstrap_javascript_is_not_loaded(self, user_1_client):
        html = page(user_1_client, 'transactions:transactions')
        assert 'bootstrap.bundle' not in html and 'data-bs-toggle' not in html


class TestTemplateSyntaxDoesNotLeak:
    """Многострочный «{# … #}» Django не считает комментарием и выводит как текст (в <head> он уезжал на страницу)."""

    @pytest.mark.parametrize('name', APP_PAGES)
    def test_app_pages(self, user_1_client, name):
        html = without_scripts(page(user_1_client, name))
        assert not re.search(r'\{#|#\}|\{%|%\}|\{\{|\}\}', html)

    @pytest.mark.parametrize('url', ['/', '/no-such-page/', '/auth/login/'])
    def test_guest_pages(self, client, url):
        html = without_scripts(client.get(url).content.decode())
        assert not re.search(r'\{#|#\}|\{%|%\}|\{\{|\}\}', html)

    def test_no_multiline_template_comments_in_sources(self):
        broken = [f'{p.relative_to(ROOT)}:{n}' for p in (ROOT / 'src' / 'templates').rglob('*.html')
                  for n, line in enumerate(p.read_text(encoding='utf-8').splitlines(), 1)
                  if '{#' in line and '#}' not in line]
        assert broken == [], 'многострочный {# #} не работает, используйте {% comment %}'


class TestStaticReferences:

    @pytest.mark.parametrize('name', APP_PAGES)
    def test_every_static_url_exists(self, user_1_client, name):
        urls = STATIC_URL.findall(page(user_1_client, name))
        assert urls
        missing = [u for u in urls if not (STATIC_DIR / u.split('?')[0].removeprefix('/static/')).is_file()]
        assert missing == []

    def test_own_assets_are_versioned_by_content(self, user_1_client):
        html = page(user_1_client, 'transactions:summary')
        assert re.search(r'/static/css/style\.css\?v=[0-9a-f]{10}"', html)
        assert re.search(r'/static/js/dashboard\.js\?v=[0-9a-f]{10}"', html)
        assert '/static/vendor/chartjs/4.4.1/chart.umd.js"' in html   # библиотеки — версия в пути, без ?v=


class TestFonts:
    css = (STATIC_DIR / 'css' / 'fonts.css').read_text(encoding='utf-8')
    declared = set(re.findall(r"url\('\.\./fonts/([^']+)'\)", css))

    def test_every_font_face_has_file_and_range(self):
        faces = re.findall(r'@font-face\s*\{(.*?)\}', self.css, flags=re.S)
        assert faces and len(faces) == len(self.declared)
        for face in faces:
            assert 'font-display: swap' in face and 'unicode-range:' in face
        assert all((STATIC_DIR / 'fonts' / name).is_file() for name in self.declared)

    def test_no_orphan_font_files(self):
        on_disk = {p.name for p in (STATIC_DIR / 'fonts').glob('*.woff2')}
        assert on_disk == self.declared

    def test_preloads_match_font_face_urls(self):
        """URL в preload должен совпасть с url() в fonts.css, иначе файл скачается дважды."""
        html = render_to_string('includes/font_preloads.html')
        preloaded = re.findall(r'href="/static/fonts/([^"?]+)"', html)
        assert len(preloaded) == 10
        assert set(preloaded) <= self.declared
        assert all('crossorigin' in tag for tag in re.findall(r'<link[^>]+>', html))

    def test_preloads_only_for_authenticated_users(self, client, user_1_client):
        assert 'rel="preload" as="font"' in page(user_1_client, 'transactions:summary')
        assert 'rel="preload" as="font"' not in client.get('/').content.decode()


class TestVersionedStorage:

    def test_version_follows_content(self, tmp_path):
        (tmp_path / 'static' / 'js').mkdir(parents=True)
        script = tmp_path / 'static' / 'js' / 'app.js'
        script.write_text('console.log(1)')
        os.utime(script, ns=(1_000_000_000, 1_000_000_000))
        with override_settings(BASE_DIR=tmp_path):
            storage = VersionedStaticFilesStorage()
            first = storage.url('js/app.js')
            assert re.fullmatch(r'/static/js/app\.js\?v=[0-9a-f]{10}', first)
            assert storage.url('js/app.js') == first
            script.write_text('console.log(2)')
            os.utime(script, ns=(2_000_000_000, 2_000_000_000))
            assert storage.url('js/app.js') != first

    def test_unversioned_paths_and_foreign_files(self):
        storage = VersionedStaticFilesStorage()
        assert UNVERSIONED_PREFIXES == ('fonts/', 'vendor/')
        assert storage.url('fonts/inter-latin-400-normal.woff2') == '/static/fonts/inter-latin-400-normal.woff2'
        assert storage.url('vendor/chartjs/4.4.1/chart.umd.js') == '/static/vendor/chartjs/4.4.1/chart.umd.js'
        assert storage.url('admin/css/base.css') == '/static/admin/css/base.css'   # не файл проекта

    def test_template_tag_uses_the_versioned_storage(self):
        assert re.fullmatch(r'/static/css/style\.css\?v=[0-9a-f]{10}', static('css/style.css'))


class TestVendoredFiles:

    def test_checksums_match_and_cover_every_file(self):
        recorded = {}
        for line in (STATIC_DIR / 'SHA256SUMS').read_text(encoding='utf-8').splitlines():
            digest, name = line.split('  ', 1)
            recorded[name] = digest
        actual = {str(p.relative_to(STATIC_DIR)) for sub in ('vendor', 'fonts') for p in (STATIC_DIR / sub).rglob('*') if p.is_file()}
        assert set(recorded) == actual, 'в SHA256SUMS и на диске разные файлы'
        for name, digest in recorded.items():
            assert hashlib.sha256((STATIC_DIR / name).read_bytes()).hexdigest() == digest, name

    def test_licenses_are_shipped_with_the_files(self):
        assert (STATIC_DIR / 'vendor' / 'bootstrap' / '5.3.3' / 'LICENSE').is_file()
        assert (STATIC_DIR / 'vendor' / 'chartjs' / '4.4.1' / 'LICENSE.md').is_file()
        assert (STATIC_DIR / 'fonts' / 'LICENSE-Inter.txt').is_file()
        assert (STATIC_DIR / 'fonts' / 'LICENSE-JetBrainsMono.txt').is_file()


class TestNginxConfigs:
    """Заголовки кеширования /static/ описаны в двух конфигах (k8s и dev) — они не должны разойтись."""

    configs = {
        'k8s': yaml.safe_load((ROOT / 'k8s' / 'configmap-nginx.yaml').read_text(encoding='utf-8'))['data']['default.conf'],
        'dev': (ROOT / 'nginx' / 'nginx.conf').read_text(encoding='utf-8'),
    }

    @staticmethod
    def static_map(conf):
        match = re.search(r'map\s+"\$uri\?\$arg_v"\s+\$static_cache_control\s*\{(.*?)\}', conf, flags=re.S)
        assert match, 'нет map для Cache-Control'
        return re.findall(r'^\s*("?~?[^\s"]+"?)\s+"([^"]+)";', match.group(1), flags=re.M)

    def test_both_configs_have_identical_cache_rules(self):
        assert self.static_map(self.configs['k8s']) == self.static_map(self.configs['dev'])

    @pytest.mark.parametrize('env', ['k8s', 'dev'])
    def test_static_location_sends_cache_control_and_gzip(self, env):
        conf = self.configs[env]
        location = re.search(r'location /static/ \{(.*?)\}', conf, flags=re.S).group(1)
        assert 'add_header Cache-Control $static_cache_control;' in location
        assert re.search(r'^\s*gzip on;', conf, flags=re.M)
        assert 'text/css' in conf and 'application/javascript' in conf

    @pytest.mark.parametrize('path, expected', [
        ('/static/css/style.css', 'no-cache'),                                    # без версии — перепроверка по ETag
        ('/static/css/style.css?', 'no-cache'),                                   # пустая версия
        ('/static/css/style.css?v=abc123def0', 'public, max-age=31536000, immutable'),
        ('/static/js/dashboard.js?v=0123456789', 'public, max-age=31536000, immutable'),
        ('/static/fonts/inter-latin-400-normal.woff2', 'public, max-age=31536000, immutable'),
        ('/static/vendor/chartjs/4.4.1/chart.umd.js', 'public, max-age=31536000, immutable'),
        ('/static/admin/css/base.css', 'no-cache'),
    ])
    def test_cache_rules_do_what_they_say(self, path, expected):
        """Правила map (регулярки nginx) применяются в порядке записи; первое совпавшее выигрывает."""
        rules = self.static_map(self.configs['k8s'])
        default = next(value for key, value in rules if key == 'default')
        result = default
        for key, value in rules:
            if key.startswith('"~') and re.search(key.strip('"')[1:], path):
                result = value
                break
        assert result == expected


def luminance(hex_color):
    channels = [int(hex_color.lstrip('#')[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    r, g, b = (c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(foreground, background):
    light, dark = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


class TestThemeContrast:
    """Светлая тема: цвет текста ≥ 4.5:1 (WCAG AA) на всех светлых фонах. Акценты --green/--red как текст
    не проходят (2.6:1 и 4.1:1), поэтому для текста есть отдельные --green-text/--red-text."""

    css = (STATIC_DIR / 'css' / 'style.css').read_text(encoding='utf-8')
    TEXT = ('--text-primary', '--text-secondary', '--text-muted', '--text-faint', '--green-text', '--red-text')
    BACKGROUNDS = ('--bg-primary', '--bg-secondary', '--bg-base', '--bg-tertiary')

    @classmethod
    def tokens(cls, block):
        return dict(re.findall(r'(--[\w-]+):\s*(#[0-9A-Fa-f]{6})\b', block))

    @classmethod
    def light_blocks(cls):
        system = re.search(r'@media \(prefers-color-scheme: light\) \{(.*?)\n\}', cls.css, flags=re.S).group(1)
        forced = re.search(r':root\[data-theme="light"\] \{(.*?)\n\}', cls.css, flags=re.S).group(1)
        return {'по системной теме': cls.tokens(system), 'по переключателю': cls.tokens(forced)}

    @pytest.mark.parametrize('block', ['по системной теме', 'по переключателю'])
    def test_light_text_tokens_are_readable(self, block):
        tokens = self.light_blocks()[block]
        weak = [f'{fg} на {bg}: {contrast(tokens[fg], tokens[bg]):.2f}'
                for fg in self.TEXT for bg in self.BACKGROUNDS if contrast(tokens[fg], tokens[bg]) < 4.5]
        assert weak == []

    def test_badges_text_is_readable_on_their_soft_background(self):
        """Бейджи доходов/расходов: текст на полупрозрачной подложке (10% акцента поверх белого)."""
        for token, accent in (('--green-text', (0, 184, 132)), ('--red-text', (230, 62, 62))):
            soft = '#%02X%02X%02X' % tuple(round(c * 0.10 + 255 * 0.90) for c in accent)
            for tokens in self.light_blocks().values():
                assert contrast(tokens[token], soft) >= 4.5, token

    def test_both_light_blocks_agree(self):
        blocks = self.light_blocks()
        assert {k: blocks['по системной теме'][k] for k in self.TEXT} == {k: blocks['по переключателю'][k] for k in self.TEXT}

    def test_dark_theme_text_accents_are_unchanged(self):
        dark = self.css[:self.css.index('/* Light theme')]
        assert '--green-text: var(--green);' in dark and '--red-text: var(--red);' in dark

    def test_text_never_uses_the_raw_accent_tokens(self):
        """color: var(--green|--red) — только через --green-text/--red-text (border-color и фоны не в счёт)."""
        raw = re.compile(r'(?<![\w-])color:\s*var\(--(green|red)\)')
        sources = [STATIC_DIR / 'css' / 'style.css', *(ROOT / 'src' / 'templates').rglob('*.html'), *(STATIC_DIR / 'js').glob('*.js')]
        offenders = [str(p.relative_to(ROOT)) for p in sources if raw.search(p.read_text(encoding='utf-8'))]
        assert offenders == []


class TestExcelHint:

    def test_hint_is_hidden_and_has_no_bootstrap_popover(self, user_1_client):
        html = page(user_1_client, 'transactions:transactions')
        assert re.search(r'<div class="export-hint" id="exportHint" role="status" hidden>', html)
        assert 'data-bs-toggle' not in html

    def test_hint_flag_is_set_by_the_webapp_entry_page_and_read_by_the_operations_page(self, user_1_client):
        webapp = render_to_string('webapp/webapp.html')
        assert "sessionStorage.setItem('ff-telegram-webapp', '1')" in webapp
        assert "sessionStorage.getItem('ff-telegram-webapp') === '1'" in page(user_1_client, 'transactions:transactions')
