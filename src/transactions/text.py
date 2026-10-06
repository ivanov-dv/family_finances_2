import re

# NUL не принимает PostgreSQL, остальные управляющие символы (кроме \t \n \r) недопустимы в XML,
# и openpyxl на них падает при выгрузке в Excel.
_CONTROL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')


def clean_text(value) -> str:
    """Убрать управляющие символы и пробелы по краям из пользовательского текста."""
    return _CONTROL_CHARS_RE.sub('', str(value or '')).strip()
