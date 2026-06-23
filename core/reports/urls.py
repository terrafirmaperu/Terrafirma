from django.urls import path
from .views.sale_report.views import SaleReportView
from .views.purchase_report.views import PurchaseReportView
from .views.expenses_report.views import ExpensesReportView
from .views.debtspay_report.views import DebtsPayReportView
from .views.ctascollect_report.views import CtasCollectReportView
from .views.results_report.views import ResultsReportView
from .views.client_report.views import ClientReportView
from .views.contracts_report.views import ContractsReportView

urlpatterns = [
    path('sale/', SaleReportView.as_view(), name='sale_report'),
    path('purchase/', PurchaseReportView.as_view(), name='purchase_report'),
    path('expenses/', ExpensesReportView.as_view(), name='expenses_report'),
    path('debts/pay/', DebtsPayReportView.as_view(), name='debtspay_report'),
    path('ctas/collect/', CtasCollectReportView.as_view(), name='ctascollect_report'),
    path('results/', ResultsReportView.as_view(), name='results_report'),
    path('clients/', ClientReportView.as_view(), name='client_report'),
    path('contracts/', ContractsReportView.as_view(), name='contracts_report'),
]
