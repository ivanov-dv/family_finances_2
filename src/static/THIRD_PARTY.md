# Сторонние файлы в static/

Собственные копии вместо CDN и fonts.bunny.net: страницы не зависят от чужих хостов, а nginx отдаёт `vendor/` и
`fonts/` с `Cache-Control: public, max-age=31536000, immutable` (версия или начертание зашиты в путь, файлы не меняются).

| Что | Версия | Файлы | Источник | Лицензия |
|---|---|---|---|---|
| Bootstrap (только CSS) | 5.3.3 | `vendor/bootstrap/5.3.3/bootstrap.min.css` | npm `bootstrap@5.3.3`, `dist/css/` | MIT (`LICENSE` рядом) |
| Chart.js | 4.4.1 | `vendor/chartjs/4.4.1/chart.umd.js` | npm `chart.js@4.4.1`, `dist/` | MIT (`LICENSE.md` рядом) |
| Inter | Fontsource 5.3.0 | `fonts/inter-{latin,latin-ext,cyrillic}-{400,500,600,700}-normal.woff2` | npm `@fontsource/inter@5.3.0`, `files/` | SIL OFL 1.1 (`fonts/LICENSE-Inter.txt`) |
| JetBrains Mono | Fontsource 5.3.0 | `fonts/jetbrains-mono-{latin,latin-ext,cyrillic}-{500,600,700}-normal.woff2` | npm `@fontsource/jetbrains-mono@5.3.0`, `files/` | SIL OFL 1.1 (`fonts/LICENSE-JetBrainsMono.txt`) |

Файлы побайтно совпадают с теми, что раньше отдавали CDN (jsDelivr, cdnjs) и fonts.bunny.net: вид и поведение страниц не изменились.
При добавлении tarball'ы сверялись с `dist.integrity` (sha512) из реестра npm; контрольные суммы лежат в `SHA256SUMS`
(`sha256sum -c SHA256SUMS` из каталога `src/static`; то же проверяет `tests/test_static_assets.py`).

Что подключено на страницах:

- `css/fonts.css` — `@font-face` для Inter и JetBrains Mono (подмножества latin, latin-ext — в нём знак ₽ — и cyrillic;
  `unicode-range` те же, что отдавал Bunny). Для десяти файлов, нужных на каждой странице приложения, в `<head>` стоит
  `preload` (`templates/includes/font_preloads.html`), поэтому шрифты готовы к первой отрисовке и текст не меняет вид.
- Bootstrap подключён только как CSS. Bootstrap JS не нужен: модалки, меню и подсказки в проекте свои. Если понадобится,
  положите `dist/js/bootstrap.bundle.min.js` рядом с CSS, добавьте в `SHA256SUMS` и подключите в `base.html` с `defer`.
- Chart.js подключён только на дашборде (`transactions/summary.html`) с `defer`.

## Как обновить библиотеку или шрифт

1. Узнайте адрес и sha512 пакета: `https://registry.npmjs.org/<пакет>/<версия>` (`dist.tarball`, `dist.integrity`).
2. Скачайте tarball в отдельный пустой каталог, сверьте sha512, достаньте нужные файлы (остальное не нужно).
3. Положите их в новый каталог с версией в пути (`vendor/<библиотека>/<версия>/`), поправьте ссылки в шаблонах
   (`base.html`, `transactions/summary.html`) и удалите старую версию. Для шрифтов имя файла содержит начертание,
   а `unicode-range` берётся из CSS Fontsource/Bunny.
4. Обновите `SHA256SUMS`: из `src/static` выполните `LC_ALL=C find vendor fonts -type f | sort | xargs sha256sum > SHA256SUMS`.
5. После выкладки `cp -r src/static/. /backend_static` (в Kubernetes это делает Job `django-collectstatic`).
