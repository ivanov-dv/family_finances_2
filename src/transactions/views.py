from django.views.generic import TemplateView

from .models import Summary


class HomePageView(TemplateView):
    template_name = 'transactions/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'FF'
        return context


class SummaryView(TemplateView):
    template_name = 'transactions/summary.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_month = self.request.user.core_settings.current_month
        current_year = self.request.user.core_settings.current_year
        current_basename = self.request.user.core_settings.current_basename
        summary = Summary.objects.filter(
            period_month=current_month,
            period_year= current_year,
            basename=current_basename
        )
        context.update(
            {
                'title': 'FF',
                'income': summary.filter(
                    type_transaction='income'
                ),
                'expense': summary.filter(
                    type_transaction='expense'
                ),
                'current_month': current_month,
                'current_year': current_year,
                'current_basename': current_basename
            }
        )
        context['title'] = 'FF'
        context['income'] = summary.filter(
            type_transaction='income'
        )
        context['expense'] = summary.filter(
            type_transaction='expense'
        )
        return context
