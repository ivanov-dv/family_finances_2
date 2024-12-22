from django.contrib.auth.decorators import login_required

from export.services import create_export_excel_transactions_response


@login_required
def export_excel(request):
    """Экспорт в excel."""
    return create_export_excel_transactions_response(request.user)
