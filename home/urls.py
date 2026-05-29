from django.contrib.auth.views import PasswordChangeView
from django.urls import path, re_path
from django.contrib.staticfiles.views import serve

from . import views

urlpatterns = [
    re_path(r'^favicon\.ico$', serve, {'path':  'icons/favicon.ico'}),
    path('', views.summary_reconciliation_view, name='summary_reconciliation_view'),
    path('printsummary_reconciliation/', views.summary_reconciliation_pdf, name='summary_reconciliation_pdf'),
    path('detail-reconciliation/', views.detail_reconciliation_view, name='detail_reconciliation_view'),
    path('detail-exemption/', views.detail_exemption_view, name='detail_exemption_view'),
    path('detail-otherpaid/', views.detail_otherpaid_view, name='detail_otherpaid_view'),
    path('account-receivables/', views.account_receivables_view, name='account_receivables_view'),
    path('revenue-summary/', views.summary_revenue_view, name='summary_revenue_view'),
    path('exam-revenue-summary/', views.summary_exam_revenue_view, name='summary_exam_revenue_view'),
    path('exam-revenue-by-patient-summary/', views.summary_exam_revenue_by_patient_view, name='summary_exam_revenue_by_patient_view'),
    path('revenue-by-dept-order-summary/', views.summary_revenue_by_dept_order_view, name='summary_revenue_by_dept_order_view'),
    path('revenue-by-dept-order-reconcile/', views.reconcile_revenue_by_dept_order_view, name='reconcile_revenue_by_dept_order_view'),
    path('detail-revenue-groupby-service/', views.detail_revenue_groupby_view, name='detail_revenue_view'),
    path('revenue-reconciliation/', views.revenue_reconciliation_view, name='revenue_reconciliation_view'),
    path('drug-retail-revenue/', views.drug_retail_revenue_view, name='drug_retail_revenue_view'),
    path('functional-food-revenue/', views.functional_food_revenue_view, name='functional_food_revenue_view'),
    path('deduction-summary/', views.summary_deduction_view, name='summary_deduction_view'),
    path('deduction-by-dept-order-summary/', views.summary_deduction_by_dept_order_view, name='summary_deduction_by_dept_order_view'),
    path('deduction-by-dept-order-reconcile/', views.reconcile_deduction_by_dept_order_view, name='reconcile_deduction_by_dept_order_view'),
    path('detail-deduction-groupby-service/', views.detail_deduction_groupby_view, name='detail_deduction_view'),
    path('drug-retail-deduction/', views.drug_retail_deduction_view, name='drug_retail_deduction_view'),
    path('cost-in-package/', views.summary_cost_in_package_by_dept_view, name='summary_cost_in_package_by_dept_view'),
    path('detail-inv-import/', views.detail_inv_import_view, name='detail_inv_import_view'),
    path('detail-inv-export/', views.detail_inv_export_view, name='detail_inv_export_view'),
    path('detail-inv-export-PDT/', views.detail_inv_export_PDT_view, name='detail_inv_export_PDT_view'),
    path('user-info/', views.user_info_view, name='user_info'),
    path('doi-mat-khau/', PasswordChangeView.as_view(
        template_name='change_password.html',
        success_url='/'
    ), name='change_password'),

]
