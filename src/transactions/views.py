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
        summary = Summary.objects.filter(
            period_month=self.request.user.core_settings.current_month,
            period_year=self.request.user.core_settings.current_year,
            basename=self.request.user.core_settings.current_basename
        )
        context['title'] = 'FF'
        context['income'] = summary.filter(
            type_transaction='income'
        )
        context['expense'] = summary.filter(
            type_transaction='expense'
        )
        return context
