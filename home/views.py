from django.shortcuts import render
from collections import defaultdict
from datetime import datetime
import pandas as pd
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
# Create your views here.
from .get_data import get_summary_reconciliation_data, get_detail_reconciliation_data, get_detail_exemption_data, get_detail_otherpaid_data, get_account_receivables_data, get_summary_revenue_data, \
get_detail_revenue_groupby_data, get_revenue_reconciliation_data, get_summary_deduction_data, get_detail_deduction_groupby_data, get_drug_retail_revenue_data, get_summary_revenue_by_dept_order_data, \
get_reconcile_revenue_by_dept_order_data, get_summary_cost_in_package_by_dept_data, get_functional_food_revenue_data, get_summary_deduction_by_dept_order_data, get_reconcile_deduction_by_dept_order_data, \
get_drug_retail_deduction_data, get_summary_exam_revenue_data,get_summary_exam_revenue_data_by_patient, get_detail_inv_import_data, get_detail_inv_export_data, get_detail_inv_export_PDT_data
from .print_templates import template_A4landscape
from .models import Cashier, PaymentMethod, Department, Storage

@login_required
class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'change_password.html'
    success_url = reverse_lazy('user_info')  # Điều hướng đến trang thông tin người dùng sau khi đổi mật khẩu

@login_required
def user_info_view(request):
    user = request.user
    context = {
        'user': user,
    }
    return render(request, 'user_info.html', context)

def format_number(data):
    for row in data:
        for key, value in row.items():
            if pd.isna(value):  # Kiểm tra nếu giá trị là NaN
                row[key] = "0"  # Thay thế NaN bằng "0" (hoặc giá trị khác tùy ý)
            elif isinstance(value, (int, float)):  # Chỉ định dạng các giá trị là số
                row[key] = f"{int(value):,}".replace(",", ".")  # Thay "," bằng "."
    return data

def format_numbers(df):
    """
    Hàm định dạng các giá trị số trong DataFrame:
    - Dấu ngăn cách hàng nghìn là dấu chấm.
    - Bỏ phần thập phân.
    """
    # Áp dụng định dạng số cho tất cả các cột có kiểu dữ liệu số
    for col in df.select_dtypes(include=['float64', 'int64']).columns:
        df[col] = df[col].apply(lambda x: f"{x:,.0f}".replace(',', '.'))  # Định dạng số, thay dấu ',' thành '.'
    return df


@login_required
def summary_reconciliation_view(request):
    payment_methods = list(PaymentMethod.objects.values_list('method', flat=True))
    check_status = [True, False]
    summary_reconciliation = pd.DataFrame()
    selected_method = None
    selected_status = None

    if request.method == 'POST':
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')
        selected_method = request.POST.get('payment_method')
        selected_status = request.POST.get('checked_status')
        # Kiểm tra nếu 'from_date' hoặc 'to_date' không có
        if not from_date or not to_date:
            return render(request, 'summary_reconciliation.html', {"error": "Please provide both from_date and to_date"})
        
        if selected_status == 'True':
            selected_status = True
        elif selected_status == 'False':
            selected_status = False
        else:
            selected_status = None
        
        summary_reconciliation = get_summary_reconciliation_data(from_date, to_date, selected_method, selected_status)
    # Chuyển DataFrame thành danh sách các từ điển (records) để hiển thị trên template
    summary_reconciliation_dict = (summary_reconciliation.to_dict(orient='records') if summary_reconciliation is not None else [])
    # Render HTML with context
    return render(
            request,
            'summary_reconciliation.html',
            { 
            "data": summary_reconciliation_dict,
            "payment_methods": payment_methods,
            "selected_method": selected_method,
            "check_status": check_status,
            "selected_status": selected_status,
            }
    )

@login_required
def detail_reconciliation_view(request):
    detail_reconciliation_by_cashier = None  # Khởi tạo giá trị mặc định cho data_reconciliation
    cashier_lists = list(Cashier.objects.values_list('name', flat=True))  # Lưu danh sách thu ngân
    payment_methods = list(PaymentMethod.objects.values_list('method', flat=True))
    check_status = [True, False]
    selected_cashier = None  # thu ngân được chọn
    selected_method = None
    selected_status = None

    if request.method == 'POST':
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')
        selected_cashier = request.POST.get('cashier_name')
        selected_method = request.POST.get('payment_method')
        selected_status = request.POST.get('checked_status')
        # Kiểm tra nếu 'from_date' hoặc 'to_date' không có
        if not from_date or not to_date:
            return render(request, 'detail_reconciliation.html', {"error": "Please provide both from_date and to_date"})
        if selected_status == 'True':
            selected_status = True
        elif selected_status == 'False':
            selected_status = False
        else:
            selected_status = None
        detail_reconciliation_by_cashier = get_detail_reconciliation_data(from_date, to_date, selected_cashier, selected_method, selected_status)

    detail_reconciliation_by_cashier_dict = (detail_reconciliation_by_cashier.to_dict(orient='records') if detail_reconciliation_by_cashier is not None else [])
    # Render HTML with context
    return render(
            request,
            'detail_reconciliation.html',
            { 
            "data": detail_reconciliation_by_cashier_dict,
            "cashier_lists": cashier_lists,
            "selected_cashier": selected_cashier,
            "payment_methods": payment_methods,
            "selected_method": selected_method,
            "check_status": check_status,
            "selected_status": selected_status,
            }
    )

@login_required
def detail_exemption_view(request):
    detail_exemption = None  # Khởi tạo giá trị mặc định cho data_reconciliation

    if request.method == 'POST':
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')
        # Kiểm tra nếu 'from_date' hoặc 'to_date' không có
        if not from_date or not to_date:
            return render(request, 'detail_reconciliation.html', {"error": "Please provide both from_date and to_date"})
        detail_exemption = get_detail_exemption_data(from_date,to_date)
    # Xử lý DataFrame nếu không rỗng và cột 'thungan' tồn tại
    detail_exemption_dict = (detail_exemption.to_dict(orient='records') if detail_exemption is not None else [])
    # Render HTML with context
    return render(
            request,
            'detail_exemption.html',
            { 
            "data": detail_exemption_dict,
            }
    )

@login_required
def detail_otherpaid_view(request):
    detail_otherpaid = None
    cashier_lists = list(Cashier.objects.values_list('name', flat=True))  # Lưu danh sách thu ngân
    selected_cashier = None  # thu ngân được chọn

    if request.method == 'POST':
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')
        selected_cashier = request.POST.get('cashier_name')
        # Kiểm tra nếu 'from_date' hoặc 'to_date' không có
        if not from_date or not to_date:
            return render(request, 'detail_otherpaid.html', {"error": "Please provide both from_date and to_date"})
        detail_otherpaid = get_detail_otherpaid_data(from_date,to_date,selected_cashier)
    detail_otherpaid_dict = (detail_otherpaid.to_dict(orient='records') if detail_otherpaid is not None else [])
    # Render HTML with context
    return render(
            request,
            'detail_otherpaid.html',
            { 
            "data": detail_otherpaid_dict,
            "cashier_lists": cashier_lists,
            "selected_cashier": selected_cashier,
            }
    )

@login_required
def account_receivables_view(request):
    account_receivables = None

    if request.method == 'POST':
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')
        # Kiểm tra nếu 'from_date' hoặc 'to_date' không có
        if not from_date or not to_date:
            return render(request, 'account_receivables.html', {"error": "Please provide both from_date and to_date"})
        account_receivables = get_account_receivables_data(from_date,to_date)
    account_receivables_dict = (account_receivables.to_dict(orient='records') if account_receivables is not None else [])
    # Render HTML with context
    return render(
            request,
            'account_receivables.html',
            { 
            "data": account_receivables_dict,
            }
    )

@login_required
def summary_revenue_view(request):
    summary_revenue = None 

    if request.method == 'POST':
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')
        #selected_method = request.POST.get('payment_method')
        #selected_status = request.POST.get('checked_status')
        # Kiểm tra nếu 'from_date' hoặc 'to_date' không có
        if not from_date or not to_date:
            return render(request, 'summary_revenue.html', {"error": "Please provide both from_date and to_date"})
        summary_revenue = get_summary_revenue_data(from_date,to_date)
    # Chuyển DataFrame thành danh sách các từ điển (records) để hiển thị trên template
    summary_revenue_dict = (summary_revenue.to_dict(orient='records') if summary_revenue is not None else [])
    # Render HTML with context
    return render(
            request,
            'summary_revenue.html',
            { 
            "data": summary_revenue_dict,
            }
    )

@login_required
def detail_revenue_groupby_view(request):
    detail_revenue_groupby = None  # Khởi tạo giá trị mặc định
    types =['DT001','DT002','DT003','DT004','DT005','DT006','DT007','DT008','DT009']
    selected_type = None
    dept_list = list(Department.objects.values('dept', 'dept_name'))
    dept_order=None
    dept_perform=None

    if request.method == 'POST':
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')
        selected_type = request.POST.get('type')
        dept_order = request.POST.get('dept_order')
        dept_perform = request.POST.get('dept_perform')
        # Kiểm tra nếu 'from_date' hoặc 'to_date' không có
        if not from_date or not to_date or not selected_type:
            return render(request, 'detail_revenue_groupby.html', {"error": "Please provide both from_date, to_date and type"})
        if selected_type not in types:
            return render(request, 'detail_revenue_groupby.html', {
                "error": f"Invalid type. Allowed types are: {', '.join(types)}"
            })
        detail_revenue_groupby = get_detail_revenue_groupby_data(from_date,to_date,selected_type,dept_order,dept_perform)
        detail_revenue_groupby = detail_revenue_groupby.groupby(['kcb_class','price_type','object_type','hft_name','hfe_group','hfe_itemid','hfe_desc','hfe_unit'],dropna=False)[['hfe_quantity','revenue']].sum().sort_values(by=['kcb_class','price_type','object_type']).reset_index()
    detail_revenue_groupby_dict = (detail_revenue_groupby.to_dict(orient='records') if detail_revenue_groupby is not None else [])
    # Render HTML with context
    return render(
            request,
            'detail_revenue_groupby.html',
            { 
            "types": types,
            "data": detail_revenue_groupby_dict,
            "dept_list": dept_list,
            "dept_order": dept_order,
            "dept_perform": dept_perform,
            }
    )

@login_required
def revenue_reconciliation_view(request):
    revenue_reconciliation = None
    check_status = [True, False]
    selected_status = None

    if request.method == 'POST':
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')
        selected_status = request.POST.get('checked_status')

        # Kiểm tra dữ liệu đầu vào
        if not from_date or not to_date:
            return render(request, 'revenue_reconciliation.html', {"error": "Please provide both from_date and to_date"})

        # Chuyển đổi selected_status sang kiểu boolean
        selected_status = selected_status == 'True' if selected_status in ['True', 'False'] else None
        revenue_reconciliation = get_revenue_reconciliation_data(from_date,to_date,selected_status)
    # Chuyển DataFrame thành danh sách từ điển
    revenue_reconciliation_dict = (revenue_reconciliation.to_dict(orient='records') if revenue_reconciliation is not None else [])

    return render(
        request,
        'revenue_reconciliation.html',
        {
            "data": revenue_reconciliation_dict,
            "check_status": check_status,
            "selected_status": selected_status,
        }
    )

@login_required
def summary_revenue_by_dept_order_view(request):
    summary_revenue_by_dept_order = None
    dept_list = list(Department.objects.values('dept', 'dept_name'))
    dept_order=None

    if request.method == 'POST':
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')
        dept_order = request.POST.get('dept_order')
        # Kiểm tra nếu 'from_date' hoặc 'to_date' không có
        if not from_date or not to_date:
            return render(request, 'summary_revenue_by_dept_order.html', {"error": "Please provide both from_date and to_date"})
        summary_revenue_by_dept_order = get_summary_revenue_by_dept_order_data(from_date,to_date,dept_order)
    # Chuyển DataFrame thành danh sách các từ điển (records) để hiển thị trên template
    summary_revenue_by_dept_order_dict = (summary_revenue_by_dept_order.to_dict(orient='records') if summary_revenue_by_dept_order is not None else [])
    # Render HTML with context
    return render(
            request,
            'summary_revenue_by_dept_order.html',
            { 
            "data": summary_revenue_by_dept_order_dict,
            "dept_list": dept_list,
            "dept_order": dept_order,
            }
    )
    
@login_required
def reconcile_revenue_by_dept_order_view(request):
    reconcile_revenue_by_dept_order = None
    dept_list = list(Department.objects.values('dept', 'dept_name'))
    dept_order=None

    if request.method == 'POST':
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')
        dept_order = request.POST.get('dept_order')
        # Kiểm tra nếu 'from_date' hoặc 'to_date' không có
        if not from_date or not to_date:
            return render(request, 'reconcile_revenue_by_dept_order.html', {"error": "Please provide both from_date and to_date"})
        reconcile_revenue_by_dept_order = get_reconcile_revenue_by_dept_order_data(from_date,to_date,dept_order)
    # Chuyển DataFrame thành danh sách các từ điển (records) để hiển thị trên template
    reconcile_revenue_by_dept_order_dict = (reconcile_revenue_by_dept_order.to_dict(orient='records') if reconcile_revenue_by_dept_order is not None else [])
    # Render HTML with context
    return render(
            request,
            'reconcile_revenue_by_dept_order.html',
            { 
            "data":reconcile_revenue_by_dept_order_dict,
            "dept_list": dept_list,
            "dept_order": dept_order,
            }
    )

@login_required
def summary_deduction_view(request):
    summary_deduction = None  # Khởi tạo giá trị mặc định cho data_reconciliation

    if request.method == 'POST':
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')
        #selected_method = request.POST.get('payment_method')
        #selected_status = request.POST.get('checked_status')
        # Kiểm tra nếu 'from_date' hoặc 'to_date' không có
        if not from_date or not to_date:
            return render(request, 'summary_deduction.html', {"error": "Please provide both from_date and to_date"})
        summary_deduction = get_summary_deduction_data(from_date,to_date)
    # Chuyển DataFrame thành danh sách các từ điển (records) để hiển thị trên template
    summary_deduction_dict = (summary_deduction.to_dict(orient='records') if summary_deduction is not None else [])
    # Render HTML with context
    return render(
            request,
            'summary_deduction.html',
            { 
            "data": summary_deduction_dict,
            }
    )

@login_required
def summary_deduction_by_dept_order_view(request):
    summary_deduction_by_dept_order = None
    dept_list = list(Department.objects.values('dept', 'dept_name'))
    dept_order=None

    if request.method == 'POST':
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')
        dept_order = request.POST.get('dept_order')
        # Kiểm tra nếu 'from_date' hoặc 'to_date' không có
        if not from_date or not to_date:
            return render(request, 'summary_deduction_by_dept_order.html', {"error": "Please provide both from_date and to_date"})
        summary_deduction_by_dept_order = get_summary_deduction_by_dept_order_data(from_date,to_date,dept_order)
    # Chuyển DataFrame thành danh sách các từ điển (records) để hiển thị trên template
    summary_deduction_by_dept_order_dict = (summary_deduction_by_dept_order.to_dict(orient='records') if summary_deduction_by_dept_order is not None else [])
    # Render HTML with context
    return render(
            request,
            'summary_deduction_by_dept_order.html',
            { 
            "data": summary_deduction_by_dept_order_dict,
            "dept_list": dept_list,
            "dept_order": dept_order,
            }
    )

@login_required
def reconcile_deduction_by_dept_order_view(request):
    reconcile_deduction_by_dept_order = None
    dept_list = list(Department.objects.values('dept', 'dept_name'))
    dept_order=None

    if request.method == 'POST':
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')
        dept_order = request.POST.get('dept_order')
        # Kiểm tra nếu 'from_date' hoặc 'to_date' không có
        if not from_date or not to_date:
            return render(request, 'reconcile_deduction_by_dept_order.html', {"error": "Please provide both from_date and to_date"})
        reconcile_deduction_by_dept_order = get_reconcile_deduction_by_dept_order_data(from_date,to_date,dept_order)
    # Chuyển DataFrame thành danh sách các từ điển (records) để hiển thị trên template
    reconcile_deduction_by_dept_order_dict = (reconcile_deduction_by_dept_order.to_dict(orient='records') if reconcile_deduction_by_dept_order is not None else [])
    # Render HTML with context
    return render(
            request,
            'reconcile_deduction_by_dept_order.html',
            { 
            "data":reconcile_deduction_by_dept_order_dict,
            "dept_list": dept_list,
            "dept_order": dept_order,
            }
    )

@login_required
def detail_deduction_groupby_view(request):
    detail_deduction_groupby = None  # Khởi tạo giá trị mặc định
    types =['DT001','DT002','DT003','DT004','DT005','DT006','DT007','DT008','DT009']
    dept_list = list(Department.objects.values('dept', 'dept_name'))
    dept_order=None
    dept_perform=None

    if request.method == 'POST':
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')
        dept_order = request.POST.get('dept_order')
        dept_perform = request.POST.get('dept_perform')
        # Kiểm tra nếu 'from_date' hoặc 'to_date' không có
        if not from_date or not to_date:
            return render(request, 'detail_deduction_groupby.html', {"error": "Please provide both from_date, to_date and type"})
        detail_deduction_groupby = get_detail_deduction_groupby_data(from_date,to_date,dept_order,dept_perform)
    detail_deduction_groupby_dict = (detail_deduction_groupby.to_dict(orient='records') if detail_deduction_groupby is not None else [])
    # Render HTML with context
    return render(
            request,
            'detail_deduction_groupby.html',
            { 
            "types": types,
            "data": detail_deduction_groupby_dict,
            "dept_list": dept_list,
            "dept_order": dept_order,
            "dept_perform": dept_perform,
            }
    )

@login_required
def drug_retail_revenue_view(request):
    drug_retail_revenue = None

    if request.method == 'POST':
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')
        # Kiểm tra nếu 'from_date' hoặc 'to_date' không có
        if not from_date or not to_date:
            return render(request, 'drug_retail_revenue.html', {"error": "Please provide both from_date and to_date"})
        drug_retail_revenue = get_drug_retail_revenue_data(from_date,to_date)
    # Chuyển DataFrame thành danh sách các từ điển (records) để hiển thị trên template
    drug_retail_revenue_dict = (drug_retail_revenue.to_dict(orient='records') if drug_retail_revenue is not None else [])
    # Render HTML with context
    return render(
            request,
            'drug_retail_revenue.html',
            { 
            "data": drug_retail_revenue_dict,
            }
    )

@login_required
def functional_food_revenue_view(request):
    functional_food_revenue = None  # Khởi tạo giá trị mặc định

    if request.method == 'POST':
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')

        # Kiểm tra nếu thiếu from_date hoặc to_date
        if not from_date or not to_date:
            return render(request, 'functional_food_revenue.html', {"error": "Please provide both from_date and to_date"})
        functional_food_revenue = get_functional_food_revenue_data (from_date,to_date)
        
    else:
        # Nếu không có POST, khởi tạo DataFrame rỗng
        functional_food_revenue = pd.DataFrame()

    # Chuyển DataFrame thành danh sách các từ điển (records) để hiển thị trên template
    functional_food_revenue_dict = (functional_food_revenue.to_dict(orient='records') if functional_food_revenue is not None else [])

    # Render HTML với context
    return render(
        request,
        'functional_food_revenue.html',
        {
            "data": functional_food_revenue_dict,
        },
    )

@login_required
def drug_retail_deduction_view(request):
    drug_retail_deduction = None

    if request.method == 'POST':
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')
        # Kiểm tra nếu 'from_date' hoặc 'to_date' không có
        if not from_date or not to_date:
            return render(request, 'drug_retail_deduction.html', {"error": "Please provide both from_date and to_date"})
        drug_retail_deduction = get_drug_retail_deduction_data(from_date,to_date)
    # Chuyển DataFrame thành danh sách các từ điển (records) để hiển thị trên template
    drug_retail_deduction_dict = (drug_retail_deduction.to_dict(orient='records') if drug_retail_deduction is not None else [])
    # Render HTML with context
    return render(
            request,
            'drug_retail_deduction.html',
            { 
            "data": drug_retail_deduction_dict,
            }
    )


@login_required
def summary_cost_in_package_by_dept_view(request):
    summary_cost_in_package_by_dept = None
    dept_list = list(Department.objects.values('dept', 'dept_name'))
    dept_perform=None

    if request.method == 'POST':
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')
        dept_perform = request.POST.get('dept_perform')
        # Kiểm tra nếu 'from_date' hoặc 'to_date' không có
        if not from_date or not to_date:
            return render(request, 'summary_cost_in_package_by_dept.html', {"error": "Please provide both from_date and to_date"})
        summary_cost_in_package_by_dept = get_summary_cost_in_package_by_dept_data(from_date,to_date,dept_perform)
    # Chuyển DataFrame thành danh sách các từ điển (records) để hiển thị trên template
    summary_cost_in_package_by_dept_dict = (summary_cost_in_package_by_dept.to_dict(orient='records') if summary_cost_in_package_by_dept is not None else [])
    # Render HTML with context
    return render(
            request,
            'summary_cost_in_package_by_dept.html',
            { 
            "data": summary_cost_in_package_by_dept_dict,
            "dept_list": dept_list,
            "dept_perform": dept_perform,
            }
    )


def summary_reconciliation_pdf(request):
    # Đăng ký các font hỗ trợ tiếng Việt
    pdfmetrics.registerFont(TTFont('TimesNewRoman', 'static/fonts/times.ttf'))
    pdfmetrics.registerFont(TTFont('TimesNewRoman-Bold', 'static/fonts/timesbd.ttf'))
    pdfmetrics.registerFont(TTFont('TimesNewRoman-Bold-Italic', 'static/fonts/timesbi.ttf'))
    pdfmetrics.registerFont(TTFont('TimesNewRoman-Italic', 'static/fonts/timesi.ttf'))

    summary_reconciliation = pd.DataFrame()
    # Lấy dữ liệu từ yêu cầu GET
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    selected_method = request.GET.get('payment_method')
    selected_status = request.GET.get('checked_status')

    # Kiểm tra nếu 'from_date' hoặc 'to_date' không có
    if not from_date or not to_date:
        return HttpResponse("Please provide both from_date and to_date", status=400)

    # Chuyển đổi giá trị selected_status thành Boolean
    if selected_status == 'True':
        selected_status = True
    elif selected_status == 'False':
        selected_status = False
    else:
        selected_status = None

    # Lấy dữ liệu từ hàm chung
    summary_reconciliation = get_summary_reconciliation_data(from_date, to_date, selected_method, selected_status)
    summary_reconciliation = summary_reconciliation.iloc[:, 0:17]
    # Tính tổng cộng cho các cột số
    numeric_columns = summary_reconciliation.select_dtypes(include=['float64', 'int64']).columns  # Lấy các cột dạng số
    totals = summary_reconciliation[numeric_columns].sum()  # Tính tổng cho các cột số

    # Tạo dòng "Tổng cộng"
    total_row = {col: 'Tổng cộng' if i == 0 else totals.get(col, '') for i, col in enumerate(summary_reconciliation.columns)}

    # Thêm dòng tổng cộng vào DataFrame
    summary_reconciliation = pd.concat([summary_reconciliation, pd.DataFrame([total_row])], ignore_index=True)
    summary_reconciliation = format_numbers(summary_reconciliation)

    try:
        from_date_obj = datetime.strptime(from_date, "%Y-%m-%d")
        to_date_obj = datetime.strptime(to_date, "%Y-%m-%d")
    except ValueError:
        return HttpResponse("Error: Invalid date format. Use 'YYYY-MM-DD'.", status=400)
    
    # Tạo response đối tượng với kiểu content là PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="summary_reconciliation.pdf"'

    # Tạo tài liệu PDF
    pdf = canvas.Canvas(response, pagesize=landscape(A4))

    # Thiết lập tiêu đề
    pdf.setFont("TimesNewRoman-Bold", 16)
    pdf.drawString(50, 550, "Summary Reconciliation Report")
    pdf.setFont("TimesNewRoman", 12)
    pdf.drawString(50, 530, f"Từ ngày: {from_date_obj.strftime('%d-%m-%Y')} đến ngày: {to_date_obj.strftime('%d-%m-%Y')}")
    pdf.drawString(50, 510, f"Hình thức: {selected_method or 'All'}")

    # Vẽ bảng nếu có dữ liệu
    if not summary_reconciliation.empty:
        # Sửa tên cột nếu cần
        summary_reconciliation.columns = ['Thu ngân', 'Hình thức', 'Hóa đơn', 'Hoàn ứng viện phí', 'Tạm ứng', 
                                          'Hóa đơn', 'Hoàn ứng viện phí', 'Trả lại tạm ứng', 'Chi khác',
                                          'Người bệnh', 'Nguồn khác', 'Miễn giảm',
                                          'Người bệnh', 'Nguồn khác', 'Miễn giảm',
                                          'Bù trừ tạm ứng',
                                          'Giảm trừ doanh thu'
                                          ]

        # Chuẩn bị dữ liệu bảng
        data = [list(summary_reconciliation.columns)] + summary_reconciliation.values.tolist()

        # Tạo bảng
        column_widths = [70, 30, 50, 40, 50, 40, 50, 40, 40, 50, 50, 40, 50, 50, 40, 50, 40]
        table = Table(data, colWidths=column_widths)
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'TimesNewRoman-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'TimesNewRoman'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
        ])
        table.setStyle(style)

        # Xác định chiều cao của bảng
        table_width, table_height = table.wrap(800, 500)

        # Nếu bảng vượt quá chiều cao trang, chia thành nhiều trang
        y_position = 450  # Vị trí bắt đầu vẽ bảng
        max_rows_per_firstpage = 20  # Số dòng tối đa trên mỗi trang
        max_rows_per_page = 25
        # Vẽ bảng với việc lặp lại hàng tiêu đề
        for i in range(0, len(data), max_rows_per_page):
            table_data = data[i:i + max_rows_per_page]
            
            # Tạo bảng cho phần dữ liệu hiện tại
            table = Table(table_data,colWidths=column_widths)
            table.setStyle(style)

            # Vẽ bảng vào trang PDF
            table_width, table_height = table.wrap(800, 500)
            table.drawOn(pdf, 50, y_position - table_height)

            # Nếu bảng chưa hết trang, thêm một trang mới và lặp lại tiêu đề
            if i + max_rows_per_page < len(data):
                pdf.showPage()
                pdf.setFont("TimesNewRoman", 8)
                y_position = 550  # Vị trí bắt đầu bảng trên trang mới

                # Vẽ lại tiêu đề cho trang mới
                title_data = [list(summary_reconciliation.columns)]  # Tiêu đề chỉ xuất hiện một lần
                title_table = Table(title_data,colWidths=column_widths)
                title_table.setStyle(style)
                title_table_width, title_table_height = title_table.wrap(800, 500)
                title_table.drawOn(pdf, 50, y_position)

    else:
        # Nếu không có dữ liệu
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(50, 450, "No data available for the selected filters.")

    # Kết thúc PDF
    pdf.showPage()
    pdf.save()

    return response

@login_required
def summary_exam_revenue_view(request):
    summary_exam_revenue = None 

    if request.method == 'POST':
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')
        #selected_method = request.POST.get('payment_method')
        #selected_status = request.POST.get('checked_status')
        # Kiểm tra nếu 'from_date' hoặc 'to_date' không có
        if not from_date or not to_date:
            return render(request, 'summary_exam_revenue.html', {"error": "Please provide both from_date and to_date"})
        summary_exam_revenue = get_summary_exam_revenue_data(from_date,to_date)
    # Chuyển DataFrame thành danh sách các từ điển (records) để hiển thị trên template
    summary_exam_revenue_dict = (summary_exam_revenue.to_dict(orient='records') if summary_exam_revenue is not None else [])
    # Render HTML with context
    return render(
            request,
            'summary_exam_revenue.html',
            { 
            "data": summary_exam_revenue_dict,
            }
    )
    
@login_required
def summary_exam_revenue_by_patient_view(request):
    summary_exam_revenue_by_patient = None 

    if request.method == 'POST':
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')
        #selected_method = request.POST.get('payment_method')
        #selected_status = request.POST.get('checked_status')
        # Kiểm tra nếu 'from_date' hoặc 'to_date' không có
        if not from_date or not to_date:
            return render(request, 'summary_exam_revenue_by_patient.html', {"error": "Please provide both from_date and to_date"})
        summary_exam_revenue_by_patient = get_summary_exam_revenue_data_by_patient(from_date,to_date)
    # Chuyển DataFrame thành danh sách các từ điển (records) để hiển thị trên template
    summary_exam_revenue_by_patient_dict = (summary_exam_revenue_by_patient.to_dict(orient='records') if summary_exam_revenue_by_patient is not None else [])
    # Render HTML with context
    return render(
            request,
            'summary_exam_revenue_by_patient.html',
            { 
            "data": summary_exam_revenue_by_patient_dict,
            }
    )

@login_required
def detail_inv_import_view(request):
    detail_inv_import = None
    from_date = request.POST.get('from_date') if request.method == 'POST' else None
    to_date = request.POST.get('to_date') if request.method == 'POST' else None
    selected_storage_ids = request.POST.getlist('storage_ids') if request.method == 'POST' else []

    if request.method == 'POST':
        if not from_date or not to_date:
            return render(request, 'detail_inv_import.html', {
                "error": "Please provide both from_date and to_date",
                "storage_list": Storage.objects.all(),
                "selected_storage_ids": selected_storage_ids,
                "from_date": from_date,
                "to_date": to_date,
                "data": []  # Trả về trống để tránh lỗi template
            })

        # Gọi hàm lấy dữ liệu (nên convert storage_ids sang int nếu cần filter DB sau đó)
        detail_inv_import = get_detail_inv_import_data(from_date, to_date, selected_storage_ids)

    # Đảm bảo truyền vào template list dữ liệu
    detail_inv_import_dict = detail_inv_import.to_dict(orient='records') if detail_inv_import is not None else []

    return render(request, 'detail_inv_import.html', {
        "data": detail_inv_import_dict,
        "storage_list": Storage.objects.all(),
        "selected_storage_ids": selected_storage_ids,
        "from_date": from_date,
        "to_date": to_date
    })

@login_required
def detail_inv_export_view(request):
    detail_inv_export = None
    from_date = request.POST.get('from_date') if request.method == 'POST' else None
    to_date = request.POST.get('to_date') if request.method == 'POST' else None
    selected_storage_ids = request.POST.getlist('storage_ids') if request.method == 'POST' else []

    if request.method == 'POST':
        if not from_date or not to_date:
            return render(request, 'detail_inv_export.html', {
                "error": "Please provide both from_date and to_date",
                "storage_list": Storage.objects.all(),
                "selected_storage_ids": selected_storage_ids,
                "from_date": from_date,
                "to_date": to_date,
                "data": []  # Trả về trống để tránh lỗi template
            })

        # Gọi hàm lấy dữ liệu (nên convert storage_ids sang int nếu cần filter DB sau đó)
        detail_inv_export = get_detail_inv_export_data(from_date, to_date, selected_storage_ids)
        # Nếu DataFrame rỗng
        if detail_inv_export is None or detail_inv_export.empty:
            return render(request, 'detail_inv_export.html', {
                "error": "Không có dữ liệu phát sinh trong khoảng thời gian đã chọn.",
                "storage_list": Storage.objects.all(),
                "selected_storage_ids": selected_storage_ids,
                "from_date": from_date,
                "to_date": to_date,
                "data": []
            })
    # Đảm bảo truyền vào template list dữ liệu
    detail_inv_export_dict = detail_inv_export.to_dict(orient='records') if detail_inv_export is not None else []

    return render(request, 'detail_inv_export.html', {
        "data": detail_inv_export_dict,
        "storage_list": Storage.objects.all(),
        "selected_storage_ids": selected_storage_ids,
        "from_date": from_date,
        "to_date": to_date
    })
    
@login_required
def detail_inv_export_PDT_view(request):
    detail_inv_export_PDT = None
    from_date = request.POST.get('from_date') if request.method == 'POST' else None
    to_date = request.POST.get('to_date') if request.method == 'POST' else None
    selected_storage_ids = request.POST.getlist('storage_ids') if request.method == 'POST' else []

    if request.method == 'POST':
        if not from_date or not to_date:
            return render(request, 'detail_inv_export_PDT.html', {
                "error": "Please provide both from_date and to_date",
                "storage_list": Storage.objects.all(),
                "selected_storage_ids": selected_storage_ids,
                "from_date": from_date,
                "to_date": to_date,
                "data": []  # Trả về trống để tránh lỗi template
            })

        # Gọi hàm lấy dữ liệu (nên convert storage_ids sang int nếu cần filter DB sau đó)
        detail_inv_export_PDT = get_detail_inv_export_PDT_data(from_date, to_date, selected_storage_ids)

    # Đảm bảo truyền vào template list dữ liệu
    detail_inv_export_PDT_dict = detail_inv_export_PDT.to_dict(orient='records') if detail_inv_export_PDT is not None else []

    return render(request, 'detail_inv_export_PDT.html', {
        "data": detail_inv_export_PDT_dict,
        "storage_list": Storage.objects.all(),
        "selected_storage_ids": selected_storage_ids,
        "from_date": from_date,
        "to_date": to_date
    })