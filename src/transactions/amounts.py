from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

# Предел DecimalField(max_digits=12, decimal_places=2) у сумм в Summary/Transaction.
MAX_AMOUNT = Decimal('9999999999.99')
CENT = Decimal('0.01')

_THOUSANDS_SEPARATORS = (' ', ' ', ' ')


class AmountError(ValueError):
    """Сумма не прошла проверку. Сообщение предназначено пользователю.

    code: invalid | too_large | negative | zero.
    """

    def __init__(self, message: str, code: str = 'invalid'):
        super().__init__(message)
        self.code = code


def parse_amount(raw, *, allow_zero=False, allow_negative=False) -> Decimal:
    """Разобрать сумму из пользовательского ввода: до копеек, в пределах MAX_AMOUNT.

    Принимает запятую как десятичный разделитель и пробелы как разделители тысяч.
    NaN/Infinity, слишком большие числа и (если не разрешено) ноль после округления
    до копеек и отрицательные значения отклоняются с AmountError.
    """
    text = str(raw or '').strip().replace(',', '.')
    for separator in _THOUSANDS_SEPARATORS:
        text = text.replace(separator, '')
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise AmountError('Введите корректную сумму.')
    if not value.is_finite():
        raise AmountError('Введите корректную сумму.')
    too_large = AmountError('Сумма слишком велика: допустимо не более 9 999 999 999,99.', 'too_large')
    if abs(value) > MAX_AMOUNT + 1:
        raise too_large
    value = value.quantize(CENT, rounding=ROUND_HALF_UP)
    if abs(value) > MAX_AMOUNT:
        raise too_large
    if value < 0 and not allow_negative:
        raise AmountError('Сумма не может быть отрицательной.', 'negative')
    if value == 0 and not allow_zero:
        raise AmountError('Сумма не может быть равна нулю.', 'zero')
    return value
