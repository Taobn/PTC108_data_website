from collections import defaultdict
from datetime import datetime
from functools import reduce
import random
import time
import pandas as pd
from .call_api import call_api_invoice_receipt,call_api_deposit,call_api_refund,call_api_revenue,call_api_deduction,call_api_ar, \
call_api_detail_revenue, call_api_detail_deduction, call_api_exam_revenue, call_api_detail_exam_revenue, call_api_detail_inv_import, \
call_api_detail_inv_export, call_api_detail_inv_export_PDT  # Import dữ liệu từ file Python khác
from .models import Cashier, PaymentMethod, Department, Storage

# Hàm gọi API với cơ chế retry
def call_api_with_retry(api_func, from_date, to_date, max_retries=3, delay=2):
    retries = 0
    while retries < max_retries:
        try:
            response = api_func(from_date, to_date)
            if response and 'data' in response and isinstance(response['data'], list):
                return response['data'] if response['data'] else []  # Trả về danh sách rỗng nếu dữ liệu blank
            else:
                print(f"API {api_func.__name__} trả về dữ liệu không hợp lệ hoặc rỗng.")
                return []
        except Exception as e:
            print(f"Lỗi khi gọi API {api_func.__name__}: {e}. Thử lại ({retries+1}/{max_retries})")
            retries += 1
            time.sleep(delay + random.uniform(0, 1))  # Tránh retry đồng loạt
    return []  # Trả về danh sách rỗng nếu API thất bại

def get_summary_reconciliation_data(from_date, to_date, selected_method=None, selected_status=None):
    # Gọi API lấy dữ liệu
    data_sources = {
        'deposit': call_api_with_retry(call_api_deposit, from_date, to_date),
        'deduction': call_api_with_retry(call_api_deduction, from_date, to_date),
        'ar': call_api_with_retry(call_api_ar, from_date, to_date),
        'receipt': call_api_with_retry(call_api_invoice_receipt, from_date, to_date),
        'refund': call_api_with_retry(call_api_refund, from_date, to_date)
    }
    
    # Chuyển dữ liệu thành DataFrame
    df = {key: pd.DataFrame(value) if value else pd.DataFrame() for key, value in data_sources.items()}
    # Ép kiểu cột hfe_invoiceno sang string nếu tồn tại trong các bảng liên quan
    for key in ['receipt', 'ar', 'refund', 'deposit', 'deduction']:
        if not df[key].empty and 'hfe_invoiceno' in df[key].columns:
            df[key]['hfe_invoiceno'] = df[key]['hfe_invoiceno'].astype(str)

    
    # Kiểm tra trước khi truy cập cột để tránh lỗi KeyError
    def safe_groupby(df, groupby_cols, agg_col, agg_func='sum', rename_col=None):
        if df.empty or not set(groupby_cols).issubset(df.columns) or agg_col not in df.columns:
            return pd.DataFrame()  # Trả về DataFrame rỗng nếu không thể groupby
        return df.groupby(groupby_cols)[agg_col].agg(agg_func).reset_index().rename(columns={agg_col: rename_col or agg_col})
    
    def safe_groupby2(df, groupby_cols, agg_dict):
        if df.empty or not all(col in df.columns for col in groupby_cols) or not all(col in df.columns for col in agg_dict.keys()):
            return pd.DataFrame(columns=groupby_cols + list(agg_dict.keys()))  # Trả về DataFrame rỗng với cột phù hợp

        return df.groupby(groupby_cols).agg(agg_dict).reset_index()

    # Xử lý lọc dữ liệu và groupby an toàn
    # Lọc các dòng trong bảng A có 'refund_type' = 1,2,3,4
    df_refund_1 = df['refund'][df['refund']['refund_type'] == 1] if not df['refund'].empty else pd.DataFrame()
    df_refund_2 = df['refund'][(df['refund']['refund_type'] == 2) & (df['refund']['hfe_payment_calc_mode'] != "M")] if not df['refund'].empty else pd.DataFrame()
    df_refund_3 = df['refund'][df['refund']['refund_type'] == 3] if not df['refund'].empty else pd.DataFrame()
    df_refund_4 = df['refund'][df['refund']['refund_type'] == 4] if not df['refund'].empty else pd.DataFrame()
    df_refund_5 = df['refund'][((df['refund']['refund_type'] == 5)) | ((df['refund']['refund_type'] == 2) & (df['refund']['hfe_payment_calc_mode'] == "M"))] if not df['refund'].empty else pd.DataFrame()
    df_invoice_receipt = df['receipt'][df['receipt']['hfe_deposit'] == 0] if not df['receipt'].empty else pd.DataFrame()
    df_invoice_advance_payment = df['receipt'][df['receipt']['hfe_deposit'] != 0] if not df['receipt'].empty else pd.DataFrame()
    df_ar_invoice_receipt = df['ar'][(df['ar']['deposit'] == 0) & (df['ar']['hfe_payment_method'] != "RC")] if not df['ar'].empty else pd.DataFrame()
    df_ar_refund = df['ar'][(df['ar']['deposit'] > 0) & (df['ar']['hfe_payment_method'] != "RC")] if not df['ar'].empty else pd.DataFrame()
    df_ar_adjust= df['ar'][(df['ar']['hfe_payment_method'] == "RC")] if not df['ar'].empty else pd.DataFrame()
    df_deposit = df['deposit'] if not df['deposit'].empty else pd.DataFrame()
    df_deduction = df['deduction'] if not df['deduction'].empty else pd.DataFrame()
    
    # Tính tổng 'hfe_payment' cho mỗi 'hfe_invoiceno', 'thungan', 'hfe_payment_method'
    df_invoice_receipt_groupby = safe_groupby(df_invoice_receipt, ['hfe_invoiceno', 'hfe_staff', 'thungan', 'hfe_payment_method'], 'hfe_payment', rename_col='invoice_receipt_amount')
    df_invoice_advance_payment_groupby = safe_groupby(df_invoice_advance_payment, ['hfe_invoiceno', 'hfe_staff', 'thungan', 'hfe_payment_method'], 'hfe_payment', rename_col='invoice_advance_payment_amount')
    df_deposit_groupby = safe_groupby(df_deposit, ['hfe_invoiceno', 'hfe_staff', 'thungan', 'hfe_payment_method'], 'hfe_amount', rename_col='deposit_amount')
    df_refund_1_groupby = safe_groupby(df_refund_1, ['hfe_invoiceno', 'hfe_staff', 'thungan', 'hfe_payment_method'], 'hfe_amount', rename_col='refund_deduction_amount')
    df_refund_2_groupby = safe_groupby(df_refund_2, ['hfe_invoiceno', 'hfe_staff', 'thungan', 'hfe_payment_method'], 'hfe_amount', rename_col='refund_after_payment_amount')
    df_refund_3_groupby = safe_groupby(df_refund_3, ['hfe_invoiceno', 'hfe_staff', 'thungan', 'hfe_payment_method'], 'hfe_amount', rename_col='return_amount')
    df_refund_4_groupby = safe_groupby(df_refund_4, ['hfe_invoiceno', 'hfe_staff', 'thungan', 'hfe_payment_method'], 'hfe_amount', rename_col='other_paid_amount')
    df_refund_5_groupby = safe_groupby(df_refund_5, ['hfe_invoiceno', 'hfe_staff', 'thungan', 'hfe_payment_method'], 'hfe_amount', rename_col='adjust_paid_amount')

    df_revenue_exemption_by_receipt_patpaid = safe_groupby(df_ar_invoice_receipt, ['hfe_invoiceno', 'hfe_staff', 'thungan', 'hfe_payment_method'], 'freeamount', rename_col='revenue_exemption_by_receipt_patpaid')
    df_revenue_by_receipt_patpaid = safe_groupby2(df_ar_invoice_receipt, ['hfe_invoiceno','hfe_staff','thungan','hfe_payment_method'], {'revenue': 'sum', 'patpaid': 'sum', 'freeamount': 'sum'})
    df_revenue_by_receipt_patpaid['revenue_by_receipt_patpaid'] = df_revenue_by_receipt_patpaid['patpaid'] - df_revenue_by_receipt_patpaid['freeamount']
    df_revenue_by_receipt_patpaid['revenue_by_receipt_otherpaid'] = df_revenue_by_receipt_patpaid['revenue'] - df_revenue_by_receipt_patpaid['patpaid']
        
    df_revenue_exemption_by_refund_patpaid = safe_groupby(df_ar_refund, ['hfe_invoiceno','hfe_staff','thungan','hfe_payment_method'], 'freeamount', rename_col='revenue_exemption_by_refund_patpaid')
    df_revenue_by_refund_patpaid = safe_groupby2(df_ar_refund, ['hfe_invoiceno','hfe_staff','thungan','hfe_payment_method'], {'revenue': 'sum', 'patpaid': 'sum', 'freeamount': 'sum'})
    df_revenue_by_refund_patpaid['revenue_by_refund_patpaid'] = df_revenue_by_refund_patpaid['patpaid'] - df_revenue_by_refund_patpaid['freeamount']
    df_revenue_by_refund_patpaid['revenue_by_refund_otherpaid'] = df_revenue_by_refund_patpaid['revenue'] - df_revenue_by_refund_patpaid['patpaid']
    
    df_revenue_exemption_by_adjust_patpaid = safe_groupby(df_ar_adjust, ['hfe_invoiceno','hfe_staff','thungan','hfe_payment_method'], 'freeamount', rename_col='revenue_exemption_by_adjust_patpaid')
    df_revenue_by_adjust_patpaid = safe_groupby2(df_ar_adjust, ['hfe_invoiceno','hfe_staff','thungan','hfe_payment_method'], {'revenue': 'sum', 'patpaid': 'sum', 'freeamount': 'sum'})
    df_revenue_by_adjust_patpaid['revenue_by_adjust_patpaid'] = df_revenue_by_adjust_patpaid['patpaid'] - df_revenue_by_adjust_patpaid['freeamount']
    df_revenue_by_adjust_patpaid['revenue_by_adjust_otherpaid'] = df_revenue_by_adjust_patpaid['revenue'] - df_revenue_by_adjust_patpaid['patpaid']

    df_revenue_by_refund_deposit = safe_groupby(df_ar_refund, ['hfe_invoiceno', 'hfe_staff', 'thungan', 'hfe_payment_method'], 'deposit', rename_col='advance_payment')
    df_deduction_groupby = safe_groupby(df_deduction, ['hfe_invoiceno'], 'revenue', rename_col='deduction')

    # Gộp hai bảng với điều kiện 'hfe_invoiceno' và 'refund_type' = 1 ở bảng A
    def safe_merge(df1, df2, on, how='inner', suffixes=('_x', '_y')):
        if df1.empty and df2.empty:
        # Nếu cả hai DataFrame rỗng, trả về DataFrame rỗng với đúng cột
            return pd.DataFrame(columns=list(set(df1.columns).union(set(df2.columns))))
        if df1.empty:
        # Nếu df1 rỗng, trả về df2 (theo kiểu 'right' hoặc 'outer')
            return df2 if how in ['right', 'outer'] else pd.DataFrame(columns=df2.columns)
        if df2.empty:
        # Nếu df2 rỗng, trả về df1 (theo kiểu 'left' hoặc 'outer')
            return df1 if how in ['left', 'outer'] else pd.DataFrame(columns=df1.columns)
    # Nếu cả hai DataFrame không rỗng, thực hiện merge bình thường
        return df1.merge(df2, on=on, how=how, suffixes=suffixes)
    
    merged_df_invoice_receipt = safe_merge(df_invoice_receipt_groupby, df_invoice_advance_payment_groupby, on=['hfe_invoiceno','hfe_staff','thungan','hfe_payment_method'], how='outer')
    merged_df_receipt = safe_merge(merged_df_invoice_receipt, df_deposit_groupby, on=['hfe_invoiceno','hfe_staff','thungan','hfe_payment_method'], how='outer')

    merged_df_refund1 = safe_merge(df_refund_1_groupby, df_refund_2_groupby, on=['hfe_invoiceno','hfe_staff','thungan','hfe_payment_method'], how='outer')
    merged_df_refund2 = safe_merge(df_refund_3_groupby, df_refund_4_groupby, on=['hfe_invoiceno','hfe_staff','thungan','hfe_payment_method'], how='outer')
    merged_df_refund3 = safe_merge(merged_df_refund2, df_refund_5_groupby, on=['hfe_invoiceno','hfe_staff','thungan','hfe_payment_method'], how='outer')
    merged_df_refund = safe_merge(merged_df_refund1, merged_df_refund3, on=['hfe_invoiceno','hfe_staff','thungan','hfe_payment_method'], how='outer')
        
    merged_df_cash_flow = safe_merge(merged_df_receipt, merged_df_refund, on=['hfe_invoiceno','hfe_staff','thungan','hfe_payment_method'], how='outer')
        
    merged_df_revenue_by_receipt_patpaid = safe_merge(merged_df_cash_flow, df_revenue_by_receipt_patpaid, on=['hfe_invoiceno','hfe_staff','thungan','hfe_payment_method'], how='outer')
    merged_df_revenue_exemption_by_receipt_patpaid = safe_merge(merged_df_revenue_by_receipt_patpaid, df_revenue_exemption_by_receipt_patpaid, on=['hfe_invoiceno','hfe_staff','thungan','hfe_payment_method'], how='outer')
    merged_df_revenue_by_refund_patpaid = safe_merge(merged_df_revenue_exemption_by_receipt_patpaid, df_revenue_by_refund_patpaid, on=['hfe_invoiceno','hfe_staff','thungan','hfe_payment_method'], how='outer')
    merged_df_revenue_exemption_by_refund_patpaid = safe_merge(merged_df_revenue_by_refund_patpaid, df_revenue_exemption_by_refund_patpaid, on=['hfe_invoiceno','hfe_staff','thungan','hfe_payment_method'], how='outer')
    merged_df_revenue_by_adjust_patpaid = safe_merge(merged_df_revenue_exemption_by_refund_patpaid, df_revenue_by_adjust_patpaid, on=['hfe_invoiceno','hfe_staff','thungan','hfe_payment_method'], how='outer')
    merged_df_revenue_by_refund_deposit = safe_merge(merged_df_revenue_by_adjust_patpaid, df_revenue_by_refund_deposit, on=['hfe_invoiceno','hfe_staff','thungan','hfe_payment_method'], how='outer')
    merged_df_deduction = safe_merge(merged_df_revenue_by_refund_deposit, df_deduction_groupby, on='hfe_invoiceno', how='outer')
        
    expected_columns = [
    'invoice_receipt_amount', 'invoice_advance_payment_amount', 'deposit_amount',
    'refund_deduction_amount', 'refund_after_payment_amount', 'return_amount',
    'other_paid_amount', 'adjust_paid_amount', 'revenue_by_receipt_patpaid', 'revenue_by_receipt_otherpaid',
    'revenue_exemption_by_receipt_patpaid', 'revenue_by_refund_patpaid',
    'revenue_by_refund_otherpaid', 'revenue_exemption_by_refund_patpaid',
    'revenue_by_adjust_patpaid', 'revenue_by_adjust_otherpaid',
    'advance_payment', 'deduction'
    ]

    # Đảm bảo DataFrame có đủ cột trước khi groupby
    for col in expected_columns:
        if col not in merged_df_deduction.columns:
            merged_df_deduction[col] = 0  # Thêm cột thiếu với giá trị 0
    
    summary_reconciliation = merged_df_deduction.groupby(['hfe_staff','thungan','hfe_payment_method'],dropna=False)[expected_columns].sum().sort_values(by=['hfe_payment_method','hfe_staff','thungan']).reset_index()
        
    tolerance = 300  # Sai số cho phép
    summary_reconciliation['comparison_criteria_1'] = summary_reconciliation['invoice_receipt_amount'] == summary_reconciliation['revenue_by_receipt_patpaid']
    summary_reconciliation['comparison_criteria_2'] = summary_reconciliation['refund_deduction_amount'] == summary_reconciliation['deduction']
    summary_reconciliation['comparison_criteria_3'] = abs((summary_reconciliation['refund_after_payment_amount'] - summary_reconciliation['invoice_advance_payment_amount']) - (summary_reconciliation['advance_payment']-summary_reconciliation['revenue_by_refund_patpaid'])) <= tolerance
    # Tổng hợp tiêu chí thứ 4 dựa trên 3 tiêu chí trước
    summary_reconciliation['comparison_criteria_4'] = (
    summary_reconciliation['comparison_criteria_1'] & 
    summary_reconciliation['comparison_criteria_2'] & 
    summary_reconciliation['comparison_criteria_3']
    )
    # Lọc theo phương thức thanh toán nếu được chọn
    
    if selected_status is not None:
    # Lọc theo cả phương thức thanh toán và trạng thái nếu cả hai đều được chọn
        if selected_method:
            summary_reconciliation = summary_reconciliation[
                (summary_reconciliation['hfe_payment_method'] == selected_method) &
                (summary_reconciliation['comparison_criteria_4'] == selected_status)
            ]   
        else:
        # Chỉ lọc theo trạng thái
            summary_reconciliation = summary_reconciliation[
                summary_reconciliation['comparison_criteria_4'] == selected_status
            ]
    elif selected_method:
    # Chỉ lọc theo phương thức thanh toán
        summary_reconciliation = summary_reconciliation[
            summary_reconciliation['hfe_payment_method'] == selected_method        ]
    # Render HTML with context
    return summary_reconciliation

def get_detail_reconciliation_data(from_date, to_date, selected_cashier=None, selected_method=None, selected_status=None):

    # Gọi API lấy dữ liệu
    data_sources = {
        'deposit': call_api_with_retry(call_api_deposit, from_date, to_date),
        'deduction': call_api_with_retry(call_api_deduction, from_date, to_date),
        'ar': call_api_with_retry(call_api_ar, from_date, to_date),
        'receipt': call_api_with_retry(call_api_invoice_receipt, from_date, to_date),
        'refund': call_api_with_retry(call_api_refund, from_date, to_date)
    }
    
    # Chuyển dữ liệu thành DataFrame
    df = {key: pd.DataFrame(value) if value else pd.DataFrame() for key, value in data_sources.items()}
    # Ép kiểu cột hfe_invoiceno sang string nếu tồn tại trong các bảng liên quan
    for key in ['receipt', 'ar', 'refund', 'deposit', 'deduction']:
        if not df[key].empty and 'hfe_invoiceno' in df[key].columns:
            df[key]['hfe_invoiceno'] = df[key]['hfe_invoiceno'].astype(str)

    
    # Kiểm tra trước khi truy cập cột để tránh lỗi KeyError
    def safe_groupby(df, groupby_cols, agg_col, agg_func='sum', rename_col=None):
        if df.empty or not set(groupby_cols).issubset(df.columns) or agg_col not in df.columns:
            return pd.DataFrame()  # Trả về DataFrame rỗng nếu không thể groupby
        return df.groupby(groupby_cols)[agg_col].agg(agg_func).reset_index().rename(columns={agg_col: rename_col or agg_col})
    
    def safe_groupby2(df, groupby_cols, agg_dict):
        if df.empty or not all(col in df.columns for col in groupby_cols) or not all(col in df.columns for col in agg_dict.keys()):
            return pd.DataFrame(columns=groupby_cols + list(agg_dict.keys()))  # Trả về DataFrame rỗng với cột phù hợp

        return df.groupby(groupby_cols).agg(agg_dict).reset_index()
    # Lọc các dòng trong bảng A có 'refund_type' = 1,2,3,4

    df_refund_1 = df['refund'][df['refund']['refund_type'] == 1] if not df['refund'].empty else pd.DataFrame()
    df_refund_2 = df['refund'][(df['refund']['refund_type'] == 2) & (df['refund']['hfe_payment_calc_mode'] != "M")] if not df['refund'].empty else pd.DataFrame()
    df_refund_3 = df['refund'][df['refund']['refund_type'] == 3] if not df['refund'].empty else pd.DataFrame()
    df_refund_4 = df['refund'][df['refund']['refund_type'] == 4] if not df['refund'].empty else pd.DataFrame()
    df_refund_5 = df['refund'][((df['refund']['refund_type'] == 5)) | ((df['refund']['refund_type'] == 2) & (df['refund']['hfe_payment_calc_mode'] == "M"))] if not df['refund'].empty else pd.DataFrame()
    df_invoice_receipt = df['receipt'][df['receipt']['hfe_deposit'] == 0] if not df['receipt'].empty else pd.DataFrame()
    df_invoice_advance_payment = df['receipt'][df['receipt']['hfe_deposit'] != 0] if not df['receipt'].empty else pd.DataFrame()
    df_ar_invoice_receipt = df['ar'][(df['ar']['deposit'] == 0) & (df['ar']['hfe_payment_method'] != "RC")] if not df['ar'].empty else pd.DataFrame()
    df_ar_refund = df['ar'][(df['ar']['deposit'] > 0) & (df['ar']['hfe_payment_method'] != "RC")] if not df['ar'].empty else pd.DataFrame()
    df_ar_adjust= df['ar'][(df['ar']['hfe_payment_method'] == "RC")] if not df['ar'].empty else pd.DataFrame()
    df_deposit = df['deposit'] if not df['deposit'].empty else pd.DataFrame()
    df_deduction = df['deduction'] if not df['deduction'].empty else pd.DataFrame()

    # Tính tổng 'hfe_payment' cho mỗi 'hfe_invoiceno', 'thungan', 'hfe_payment_method'
    df_invoice_receipt_groupby = df_invoice_receipt.groupby(['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'])['hfe_payment'].sum().reset_index().rename(columns={'hfe_payment': 'invoice_receipt_amount'})
    df_invoice_advance_payment_groupby = df_invoice_advance_payment.groupby(['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'])['hfe_payment'].sum().reset_index().rename(columns={'hfe_payment': 'invoice_advance_payment_amount'})
    df_deposit_groupby = df['deposit'].groupby(['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'])['hfe_amount'].sum().reset_index().rename(columns={'hfe_amount': 'deposit_amount'})
    df_refund_1_groupby = df_refund_1.groupby(['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'])['hfe_amount'].sum().reset_index().rename(columns={'hfe_amount': 'refund_deduction_amount'})
    df_refund_2_groupby = df_refund_2.groupby(['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'])['hfe_amount'].sum().reset_index().rename(columns={'hfe_amount': 'refund_after_payment_amount'})
    df_refund_3_groupby = df_refund_3.groupby(['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'])['hfe_amount'].sum().reset_index().rename(columns={'hfe_amount': 'return_amount'})
    df_refund_4_groupby = df_refund_4.groupby(['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'])['hfe_amount'].sum().reset_index().rename(columns={'hfe_amount': 'other_paid_amount'})
    df_refund_5_groupby = df_refund_5.groupby(['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'])['hfe_amount'].sum().reset_index().rename(columns={'hfe_amount': 'adjust_paid_amount'})

    df_revenue_exemption_by_receipt_patpaid = df_ar_invoice_receipt.groupby(['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'])['freeamount'].sum().reset_index().rename(columns={'freeamount': 'revenue_exemption_by_receipt_patpaid'})
    df_revenue_by_receipt_patpaid = df_ar_invoice_receipt.groupby(['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method']).agg({'revenue': 'sum', 'patpaid': 'sum', 'freeamount': 'sum'}).reset_index()
    df_revenue_by_receipt_patpaid['revenue_by_receipt_patpaid'] = df_revenue_by_receipt_patpaid['patpaid'] - df_revenue_by_receipt_patpaid['freeamount']
    df_revenue_by_receipt_patpaid['revenue_by_receipt_otherpaid'] = df_revenue_by_receipt_patpaid['revenue'] - df_revenue_by_receipt_patpaid['patpaid']
        
    df_revenue_exemption_by_refund_patpaid = df_ar_refund.groupby(['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'])['freeamount'].sum().reset_index().rename(columns={'freeamount': 'revenue_exemption_by_refund_patpaid'})
    df_revenue_by_refund_patpaid = df_ar_refund.groupby(['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method']).agg({'revenue': 'sum', 'patpaid': 'sum', 'freeamount': 'sum'}).reset_index()
    df_revenue_by_refund_patpaid['revenue_by_refund_patpaid'] = df_revenue_by_refund_patpaid['patpaid'] - df_revenue_by_refund_patpaid['freeamount']
    df_revenue_by_refund_patpaid['revenue_by_refund_otherpaid'] = df_revenue_by_refund_patpaid['revenue'] - df_revenue_by_refund_patpaid['patpaid']
    
    df_revenue_exemption_by_adjust_patpaid = df_ar_adjust.groupby(['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'])['freeamount'].sum().reset_index().rename(columns={'freeamount': 'revenue_exemption_by_adjust_patpaid'})
    df_revenue_by_adjust_patpaid = df_ar_adjust.groupby(['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method']).agg({'revenue': 'sum', 'patpaid': 'sum', 'freeamount': 'sum'}).reset_index()
    df_revenue_by_adjust_patpaid['revenue_by_adjust_patpaid'] = df_revenue_by_adjust_patpaid['patpaid'] - df_revenue_by_adjust_patpaid['freeamount']
    df_revenue_by_adjust_patpaid['revenue_by_adjust_otherpaid'] = df_revenue_by_adjust_patpaid['revenue'] - df_revenue_by_adjust_patpaid['patpaid']

    df_revenue_by_refund_deposit = df_ar_refund.groupby(['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'])['deposit'].sum().reset_index().rename(columns={'deposit': 'advance_payment'})

    df_deduction_groupby = df['deduction'].groupby(['hfe_docno_1','hfe_invoiceno'])['revenue'].sum().reset_index().rename(columns={'revenue': 'deduction'})

    # Gộp hai bảng với điều kiện 'hfe_invoiceno' và 'refund_type' = 1 ở bảng A
    merged_df_invoice_receipt = pd.merge(df_invoice_receipt_groupby, df_invoice_advance_payment_groupby, on=['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'], how='outer')
    merged_df_receipt = pd.merge(merged_df_invoice_receipt, df_deposit_groupby, on=['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'], how='outer')

    merged_df_refund1 = pd.merge(df_refund_1_groupby, df_refund_2_groupby, on=['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'], how='outer')
    merged_df_refund2 = pd.merge(df_refund_3_groupby, df_refund_4_groupby, on=['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'], how='outer')
    merged_df_refund3 = pd.merge(merged_df_refund2, df_refund_5_groupby, on=['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'], how='outer')
    merged_df_refund = pd.merge(merged_df_refund1, merged_df_refund3, on=['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'], how='outer')
        
    merged_df_cash_flow = pd.merge(merged_df_receipt, merged_df_refund, on=['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'], how='outer')
        
    merged_df_revenue_by_receipt_patpaid = pd.merge(merged_df_cash_flow, df_revenue_by_receipt_patpaid, on=['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'], how='outer')
    merged_df_revenue_exemption_by_receipt_patpaid = pd.merge(merged_df_revenue_by_receipt_patpaid, df_revenue_exemption_by_receipt_patpaid, on=['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'], how='outer')
    merged_df_revenue_by_refund_patpaid = pd.merge(merged_df_revenue_exemption_by_receipt_patpaid, df_revenue_by_refund_patpaid, on=['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'], how='outer')
    merged_df_revenue_exemption_by_refund_patpaid = pd.merge(merged_df_revenue_by_refund_patpaid, df_revenue_exemption_by_refund_patpaid, on=['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'], how='outer')
    merged_df_revenue_by_adjust_patpaid = pd.merge(merged_df_revenue_exemption_by_refund_patpaid, df_revenue_by_adjust_patpaid, on=['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'], how='outer')
    merged_df_revenue_by_refund_deposit = pd.merge(merged_df_revenue_by_adjust_patpaid, df_revenue_by_refund_deposit, on=['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'], how='outer')
    merged_df_deduction = pd.merge(merged_df_revenue_by_refund_deposit, df_deduction_groupby, on=['hfe_docno_1','hfe_invoiceno'], how='outer')
        
    detail_reconciliation_by_cashier = merged_df_deduction.groupby(['hfe_docno_1','thungan','hfe_payment_method'],dropna=False)[['invoice_receipt_amount',
                                                                                                             'invoice_advance_payment_amount',
                                                                                                             'deposit_amount',
                                                                                                             'refund_deduction_amount',
                                                                                                             'refund_after_payment_amount',
                                                                                                             'return_amount',
                                                                                                             'other_paid_amount',
                                                                                                             'adjust_paid_amount',
                                                                                                             'revenue_by_receipt_patpaid',
                                                                                                             'revenue_by_receipt_otherpaid',
                                                                                                             'revenue_exemption_by_receipt_patpaid',
                                                                                                             'revenue_by_refund_patpaid',
                                                                                                             'revenue_by_refund_otherpaid',
                                                                                                             'revenue_exemption_by_refund_patpaid',
                                                                                                             'revenue_by_adjust_patpaid',
                                                                                                             'revenue_by_adjust_otherpaid',
                                                                                                             'advance_payment',
                                                                                                             'deduction'
                                                                                                             ]].sum().sort_values(by=['hfe_payment_method','thungan']).reset_index()
        
    tolerance = 100  # Sai số cho phép
    detail_reconciliation_by_cashier['comparison_criteria_1'] = detail_reconciliation_by_cashier['invoice_receipt_amount'] == detail_reconciliation_by_cashier['revenue_by_receipt_patpaid']
    detail_reconciliation_by_cashier['comparison_criteria_2'] = detail_reconciliation_by_cashier['refund_deduction_amount'] == detail_reconciliation_by_cashier['deduction']
    detail_reconciliation_by_cashier['comparison_criteria_3'] = abs((detail_reconciliation_by_cashier['refund_after_payment_amount'] - detail_reconciliation_by_cashier['invoice_advance_payment_amount']) - (detail_reconciliation_by_cashier['advance_payment']-detail_reconciliation_by_cashier['revenue_by_refund_patpaid'])) <= tolerance
    # Tổng hợp tiêu chí thứ 4 dựa trên 3 tiêu chí trước
    detail_reconciliation_by_cashier['comparison_criteria_4'] = (
    detail_reconciliation_by_cashier['comparison_criteria_1'] & 
    detail_reconciliation_by_cashier['comparison_criteria_2'] & 
    detail_reconciliation_by_cashier['comparison_criteria_3']
    )
    # Now, after processing the data, let's extract unique cashiers and payment methods
    if detail_reconciliation_by_cashier is not None and not detail_reconciliation_by_cashier.empty:
        # Extract unique 'thungan' (cashiers) and 'hfe_payment_method' (payment methods)
        unique_cashiers = detail_reconciliation_by_cashier['thungan'].dropna().unique()
        unique_payment_methods = detail_reconciliation_by_cashier['hfe_payment_method'].dropna().unique()

        # Save unique cashiers to the database (avoid duplicates)
        for cashier_name in unique_cashiers:
            Cashier.objects.get_or_create(name=cashier_name)
            
        # Save unique payment methods to the database (avoid duplicates)
        for method in unique_payment_methods:
            PaymentMethod.objects.get_or_create(method=method)

    # Lọc theo phương thức thanh toán nếu được chọn
    if selected_status is not None:
    # Lọc theo trạng thái trước nếu trạng thái được chọn
        if selected_cashier and selected_method:
            detail_reconciliation_by_cashier = detail_reconciliation_by_cashier[
                (detail_reconciliation_by_cashier['comparison_criteria_4'] == selected_status) &
                (detail_reconciliation_by_cashier['thungan'] == selected_cashier) &
                (detail_reconciliation_by_cashier['hfe_payment_method'] == selected_method)
            ]
        elif selected_cashier:
            detail_reconciliation_by_cashier = detail_reconciliation_by_cashier[
                (detail_reconciliation_by_cashier['comparison_criteria_4'] == selected_status) &
                (detail_reconciliation_by_cashier['thungan'] == selected_cashier)
            ]
        elif selected_method:
            detail_reconciliation_by_cashier = detail_reconciliation_by_cashier[
                (detail_reconciliation_by_cashier['comparison_criteria_4'] == selected_status) &
                (detail_reconciliation_by_cashier['hfe_payment_method'] == selected_method)
            ]
        else:
            detail_reconciliation_by_cashier = detail_reconciliation_by_cashier[
                detail_reconciliation_by_cashier['comparison_criteria_4'] == selected_status
            ]
    elif selected_cashier and selected_method:
    # Nếu trạng thái không được chọn, lọc theo thu ngân và phương thức thanh toán
        detail_reconciliation_by_cashier = detail_reconciliation_by_cashier[
            (detail_reconciliation_by_cashier['thungan'] == selected_cashier) &
            (detail_reconciliation_by_cashier['hfe_payment_method'] == selected_method)
        ]
    elif selected_cashier:
    # Nếu chỉ thu ngân được chọn, lọc theo thu ngân
        detail_reconciliation_by_cashier = detail_reconciliation_by_cashier[
            detail_reconciliation_by_cashier['thungan'] == selected_cashier
        ]
    elif selected_method:
    # Nếu chỉ phương thức thanh toán được chọn, lọc theo phương thức thanh toán
        detail_reconciliation_by_cashier = detail_reconciliation_by_cashier[
            detail_reconciliation_by_cashier['hfe_payment_method'] == selected_method
        ]
    # Lấy danh sách các phương thức thanh toán từ dữ liệu
    # Xử lý DataFrame nếu không rỗng và cột 'thungan' tồn tại
    cashier_lists_db = list(Cashier.objects.values_list('name', flat=True))
    if detail_reconciliation_by_cashier is not None and not detail_reconciliation_by_cashier.empty:
        if 'thungan' in detail_reconciliation_by_cashier.columns:
            cashier_lists_df = detail_reconciliation_by_cashier['thungan'].dropna().unique().tolist()
        else:
            cashier_lists_df = []
    else:
        cashier_lists_df = []
    cashier_lists = list(set(cashier_lists_db + cashier_lists_df))
    for name in cashier_lists:
        if not Cashier.objects.filter(name=name).exists():
            Cashier.objects.create(name=name)

    payment_methods_db = list(PaymentMethod.objects.values_list('method', flat=True))
    if detail_reconciliation_by_cashier is not None and not detail_reconciliation_by_cashier.empty:
        if 'hfe_payment_method' in detail_reconciliation_by_cashier.columns:
            payment_methods_df = detail_reconciliation_by_cashier['hfe_payment_method'].dropna().unique().tolist()
        else:
            payment_methods_df = []
    else:
        payment_methods_df = []
    payment_methods = list(set(payment_methods_db + payment_methods_df))

    return detail_reconciliation_by_cashier

def get_detail_exemption_data(from_date,to_date):

    ar_series = call_api_ar(from_date,to_date)['data']
    df_ar = pd.DataFrame(ar_series)
    df_ar_invoice_receipt = df_ar[(df_ar['deposit'] == 0)]
    df_ar_refund = df_ar[(df_ar['deposit'] > 0)]

    # Tính tổng 'hfe_payment' cho mỗi 'hfe_invoiceno', 'thungan', 'hfe_payment_method'
    df_revenue_exemption_by_receipt_patpaid = df_ar_invoice_receipt.groupby(['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'])['freeamount'].sum().reset_index().rename(columns={'freeamount': 'revenue_exemption_by_receipt_patpaid'})
    df_revenue_by_receipt_patpaid = df_ar_invoice_receipt.groupby(['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method']).agg({'revenue': 'sum', 'patpaid': 'sum', 'freeamount': 'sum'}).reset_index()
    df_revenue_by_receipt_patpaid['revenue_by_receipt_patpaid'] = df_revenue_by_receipt_patpaid['patpaid'] - df_revenue_by_receipt_patpaid['freeamount']
    df_revenue_by_receipt_patpaid['revenue_by_receipt_otherpaid'] = df_revenue_by_receipt_patpaid['revenue'] - df_revenue_by_receipt_patpaid['patpaid']
        
    df_revenue_exemption_by_refund_patpaid = df_ar_refund.groupby(['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'])['freeamount'].sum().reset_index().rename(columns={'freeamount': 'revenue_exemption_by_refund_patpaid'})
    df_revenue_by_refund_patpaid = df_ar_refund.groupby(['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method']).agg({'revenue': 'sum', 'patpaid': 'sum', 'freeamount': 'sum'}).reset_index()
    df_revenue_by_refund_patpaid['revenue_by_refund_patpaid'] = df_revenue_by_refund_patpaid['patpaid'] - df_revenue_by_refund_patpaid['freeamount']
    df_revenue_by_refund_patpaid['revenue_by_refund_otherpaid'] = df_revenue_by_refund_patpaid['revenue'] - df_revenue_by_refund_patpaid['patpaid']

    df_revenue_by_refund_deposit = df_ar_refund.groupby(['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'])['deposit'].sum().reset_index().rename(columns={'deposit': 'advance_payment'})

    # Gộp hai bảng với điều kiện 'hfe_invoiceno' và 'refund_type' = 1 ở bảng A
    merged_df_revenue_exemption_by_receipt_patpaid = pd.merge(df_revenue_by_receipt_patpaid, df_revenue_exemption_by_receipt_patpaid, on=['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'], how='outer')
    merged_df_revenue_by_refund_patpaid = pd.merge(merged_df_revenue_exemption_by_receipt_patpaid, df_revenue_by_refund_patpaid, on=['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'], how='outer')
    merged_df_revenue_exemption_by_refund_patpaid = pd.merge(merged_df_revenue_by_refund_patpaid, df_revenue_exemption_by_refund_patpaid, on=['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'], how='outer')
    merged_df_revenue_by_refund_deposit = pd.merge(merged_df_revenue_exemption_by_refund_patpaid, df_revenue_by_refund_deposit, on=['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method'], how='outer')
        
    merged_df_revenue_by_refund_deposit = merged_df_revenue_by_refund_deposit[
        (merged_df_revenue_by_refund_deposit['revenue_exemption_by_receipt_patpaid']>0)|
        (merged_df_revenue_by_refund_deposit['revenue_exemption_by_refund_patpaid']>0)
        ]
    detail_exemption = merged_df_revenue_by_refund_deposit.groupby(['hfe_docno_1','thungan','hfe_payment_method'],dropna=False)[['revenue_by_receipt_patpaid',
                                                                                                             'revenue_by_receipt_otherpaid',
                                                                                                             'revenue_exemption_by_receipt_patpaid',
                                                                                                             'revenue_by_refund_patpaid',
                                                                                                             'revenue_by_refund_otherpaid',
                                                                                                             'revenue_exemption_by_refund_patpaid',
                                                                                                             'advance_payment',
                                                                                                             ]].sum().sort_values(by=['hfe_docno_1','hfe_payment_method','thungan']).reset_index()
    return detail_exemption

def get_detail_otherpaid_data(from_date,to_date,selected_cashier=None):
    refund_series = call_api_refund(from_date,to_date)['data']
    df_refund = pd.DataFrame(refund_series)
    # Lọc các dòng trong bảng A có 'refund_type' = 1,2,3,4
    df_otherpaid = df_refund[(df_refund['refund_type'] == 4)]

    # Tính tổng 'hfe_payment' cho mỗi 'hfe_invoiceno', 'thungan', 'hfe_payment_method'
    detail_otherpaid = df_otherpaid.groupby(['hfe_docno_1','hp_name','hfe_invoiceno','thungan','hfe_payment_method','hfe_desc'])['hfe_amount'].sum().reset_index().rename(columns={'hfe_amount': 'other_paid_amount'}).sort_values(by=['thungan']).reset_index()
    if detail_otherpaid is not None and not detail_otherpaid.empty:
    # Lọc theo phương thức thanh toán nếu được chọn
        if selected_cashier is not None:
    # Lọc theo trạng thái trước nếu trạng thái được chọn
            [(detail_otherpaid['thungan'] == selected_cashier)]
    return detail_otherpaid

def get_account_receivables_data(from_date,to_date):
    ar_series = call_api_ar(from_date,to_date)['data']
    df_ar = pd.DataFrame(ar_series)
    df_ar_insurance_hn = df_ar[(df_ar['receipt_object'] == 1)]
    df_ar_insurance_bqp = df_ar[(df_ar['receipt_object'] == 2)]
    df_ar_insurance_ctc = df_ar[(df_ar['receipt_object'] == 3)]
        
    # Tính tổng theo điều kiện
    df_insurance_hn_receivable = df_ar_insurance_hn.groupby(['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method','hd_cardno','hfe_date'])['insurance'].sum().reset_index().rename(columns={'insurance': 'insurance_hn_receivable'})
    df_cuctaichinh_bqp_receivable = df_ar_insurance_hn.groupby(['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method','hd_cardno','hfe_date'])['bqp'].sum().reset_index().rename(columns={'bqp': 'cuctaichinh_bqp_receivable'})
    df_cuctaichinh_bqp_receivable2 = df_ar_insurance_ctc.groupby(['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method','hd_cardno','hfe_date'], dropna=False).agg({'insurance': 'sum', 'bqp': 'sum'}).reset_index()
    df_cuctaichinh_bqp_receivable2['cuctaichinh_bqp_receivable'] = df_cuctaichinh_bqp_receivable2['insurance'] + df_cuctaichinh_bqp_receivable2['bqp']
    df_insurance_bqp_receivable = df_ar_insurance_bqp.groupby(['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method','hd_cardno','hfe_date']).agg({'insurance': 'sum', 'bqp': 'sum'}).reset_index()
    df_insurance_bqp_receivable['insurance_bqp_receivable'] = df_insurance_bqp_receivable['insurance'] + df_insurance_bqp_receivable['bqp']
        
    # Gộp bảng với điều kiện
    merged_df_insurance_ctc_receivable = pd.concat([df_cuctaichinh_bqp_receivable, df_cuctaichinh_bqp_receivable2], ignore_index=True)
    merged_df_insurance_hn_receivable = pd.merge(merged_df_insurance_ctc_receivable, df_insurance_hn_receivable, on=['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method','hd_cardno','hfe_date'], how='outer')
    merged_df_insurance_bqp_receivable = pd.merge(merged_df_insurance_hn_receivable, df_insurance_bqp_receivable, on=['hfe_docno_1','hfe_invoiceno','thungan','hfe_payment_method','hd_cardno','hfe_date'], how='outer')
        
   # Tổng hợp dữ liệu
    account_receivables = merged_df_insurance_bqp_receivable.groupby(
        ['hfe_docno_1', 'thungan', 'hfe_payment_method', 'hd_cardno', 'hfe_date'], dropna=False
    )[['insurance_hn_receivable', 'insurance_bqp_receivable', 'cuctaichinh_bqp_receivable']].sum().reset_index()

    # Định dạng lại cột ngày tháng
    account_receivables['hfe_date'] = pd.to_datetime(account_receivables['hfe_date']).dt.strftime('%d/%m/%Y')

    # Sắp xếp dữ liệu theo ngày, phương thức thanh toán và thu ngân
    account_receivables = account_receivables.sort_values(by=['hfe_date', 'hfe_payment_method', 'thungan']).reset_index(drop=True)
    return account_receivables

def get_summary_revenue_data(from_date,to_date):
    revenue_series = call_api_revenue(from_date,to_date)['data']
    ar_series = call_api_ar(from_date,to_date)['data']
    df_revenue = pd.DataFrame(revenue_series)
    df_ar = pd.DataFrame(ar_series)

    # Tách dữ liệu theo điều kiện drug_retail
    df_revenue_except_drug_retail = df_revenue.query("drug_retail == 'N'")
    df_revenue_drug_retail = df_revenue.query("drug_retail == 'Y'")
    
    # Tạo danh sách các hft_id2 và tên cột tương ứng
    hft_mappings = {
        'DT001': 'tien_kham',
        'DT002': 'tien_giuong',
        'DT003': 'tien_cls',
        'DT004': 'tien_pttt',
        'DT005': 'tien_thuoc',
        'DT006': 'tien_vattu',
        'DT007': 'tien_thuoc_pm',
        'DT008': 'tien_vattu_pm',
        'DT009': 'tien_khac',
        }

    # Tạo DataFrame tổng hợp từng nhóm
    grouped_dataframes = []
    for hft_id, column_name in hft_mappings.items():
        df_filtered = df_revenue_except_drug_retail[df_revenue_except_drug_retail['hft_id2'] == hft_id]
        df_grouped = df_filtered.groupby(['kcb_class', 'price_type', 'object_type'])['revenue'] \
                            .sum().reset_index().rename(columns={'revenue': column_name})
        grouped_dataframes.append(df_grouped)

    df_total_revenue_except_drug_retail = reduce(lambda left, right: pd.merge(left, right, on=['kcb_class', 'price_type', 'object_type'], how='outer'), grouped_dataframes)

    # Thêm tổng doanh thu từ df_ar
    df_total_drug_retail = df_revenue_drug_retail.groupby(['kcb_class', 'price_type', 'object_type'])['revenue'].sum().reset_index().rename(columns={'revenue': 'drug_retail'})
    df_total_revenue_by_invoice = df_ar.groupby(['kcb_class', 'price_type', 'object_type'])['revenue'].sum().reset_index()
    total_revenue = pd.merge(df_total_revenue_except_drug_retail, df_total_drug_retail, on=['kcb_class', 'price_type', 'object_type'], how='outer')
    summary_revenue = pd.merge(total_revenue, df_total_revenue_by_invoice, on=['kcb_class', 'price_type', 'object_type'], how='outer')

    # Sắp xếp dữ liệu
    summary_revenue = summary_revenue.groupby(['kcb_class', 'price_type', 'object_type'], dropna=False).sum().reset_index()
    summary_revenue['kcb_class'] = summary_revenue['kcb_class'].replace({1: 'Ngoại trú', 2: 'Nội trú'})
    summary_revenue['price_type'] = summary_revenue['price_type'].replace({1: 'Thông thường', 2: 'Theo yêu cầu'})
    summary_revenue['object_type'] = summary_revenue['object_type'].replace({1: 'BHYT', 2: 'Dịch vụ'})
    return summary_revenue

def get_summary_revenue_by_dept_order_data(from_date, to_date, dept_order=None):
    # Lấy dữ liệu từ API
    revenue_series = call_api_with_retry(call_api_revenue,from_date, to_date)
    df_revenue = pd.DataFrame(revenue_series)
    
    # Tách dữ liệu theo điều kiện drug_retail
    df_revenue_except_drug_retail = df_revenue.query("drug_retail == 'N'")
    df_revenue_drug_retail = df_revenue.query("drug_retail == 'Y'")
    
    # Tạo danh sách các hft_id2 và tên cột tương ứng
    hft_mappings = {
        'DT001': 'tien_kham',
        'DT002': 'tien_giuong',
        'DT003': 'tien_cls',
        'DT004': 'tien_pttt',
        'DT005': 'tien_thuoc',
        'DT006': 'tien_vattu',
        'DT007': 'tien_thuoc_pm',
        'DT008': 'tien_vattu_pm',
        'DT009': 'tien_khac',
    }

    # Tạo DataFrame tổng hợp từng nhóm
    grouped_dataframes = []
    for hft_id, column_name in hft_mappings.items():
        df_filtered = df_revenue_except_drug_retail[df_revenue_except_drug_retail['hft_id2'] == hft_id]
        df_grouped = df_filtered.groupby(['kcb_class', 'price_type', 'object_type','sd_makhoa_taichinh_order'])['revenue'] \
            .sum().reset_index().rename(columns={'revenue': column_name})
        grouped_dataframes.append(df_grouped)

    # Merge tất cả các DataFrame
    revenue_except_drug_retail = reduce(
        lambda left, right: pd.merge(left, right, on=['kcb_class', 'price_type', 'object_type','sd_makhoa_taichinh_order'], how='outer'),
        grouped_dataframes
    )

    # Lấy danh sách phòng ban từ cơ sở dữ liệu và dữ liệu API
    dept_list_db = list(Department.objects.values_list('dept', flat=True))
    if revenue_except_drug_retail is not None and not revenue_except_drug_retail.empty:
        if 'sd_makhoa_taichinh_order' in revenue_except_drug_retail.columns:
            dept_list_df = revenue_except_drug_retail['sd_makhoa_taichinh_order'].dropna().unique().tolist()
        else:
            dept_list_df = []
    else:
        dept_list_df = []
    dept_list = list(set(dept_list_db + dept_list_df))
    
    for dept in dept_list:
        if not Department.objects.filter(dept=dept).exists():
            Department.objects.create(dept=dept)

    # Tổng hợp dữ liệu và nhóm theo phòng ban
    total_drug_retail = df_revenue_drug_retail.groupby(['kcb_class', 'price_type', 'object_type','sd_makhoa_taichinh_order'])['revenue'].sum().reset_index().rename(columns={'revenue': 'drug_retail'})
    summary_revenue = pd.merge(revenue_except_drug_retail, total_drug_retail, on=['kcb_class', 'price_type', 'object_type','sd_makhoa_taichinh_order'], how='outer')
    summary_revenue_by_dept_order = summary_revenue.groupby(
        ['sd_makhoa_taichinh_order', 'kcb_class', 'price_type', 'object_type'], dropna=False
    ).sum().reset_index()
    summary_revenue_by_dept_order['kcb_class'] = summary_revenue_by_dept_order['kcb_class'].replace({1: 'Ngoại trú', 2: 'Nội trú'})
    summary_revenue_by_dept_order['price_type'] = summary_revenue_by_dept_order['price_type'].replace({1: 'Thông thường', 2: 'Theo yêu cầu'})
    summary_revenue_by_dept_order['object_type'] = summary_revenue_by_dept_order['object_type'].replace({1: 'BHYT', 2: 'Dịch vụ'})

    # Lọc theo phòng ban nếu có
    if dept_order:
        summary_revenue_by_dept_order = summary_revenue_by_dept_order[
            summary_revenue_by_dept_order['sd_makhoa_taichinh_order'] == dept_order
        ]

    return summary_revenue_by_dept_order

def get_detail_revenue_groupby_data(from_date,to_date,selected_type,dept_order=None,dept_perform=None):
    detail_revenue_series = call_api_detail_revenue(from_date,to_date,selected_type)['data']
    df_detail_revenue = pd.DataFrame(detail_revenue_series)
    detail_revenue_groupby = df_detail_revenue.groupby(['kcb_class','price_type','object_type','hft_name','hfe_group','hfe_itemid','hfe_desc','sd_makhoa_taichinh_order','sd_makhoa_taichinh','hfe_unit'],dropna=False)[['hfe_quantity','revenue']].sum().sort_values(by=['kcb_class','price_type','object_type']).reset_index()
    detail_revenue_groupby['kcb_class'] = detail_revenue_groupby['kcb_class'].replace({1: 'Ngoại trú', 2: 'Nội trú'})
    detail_revenue_groupby['price_type'] = detail_revenue_groupby['price_type'].replace({1: 'Thông thường', 2: 'Theo yêu cầu'})
    detail_revenue_groupby['object_type'] = detail_revenue_groupby['object_type'].replace({1: 'BHYT', 2: 'Dịch vụ'})
    # Lấy danh sách phòng ban từ cơ sở dữ liệu và dữ liệu API
    dept_list_db = list(Department.objects.values_list('dept', flat=True))
    if detail_revenue_groupby is not None and not detail_revenue_groupby.empty:
        if 'sd_makhoa_taichinh' in detail_revenue_groupby.columns:
            dept_list_df = detail_revenue_groupby['sd_makhoa_taichinh'].dropna().unique().tolist()
        else:
            dept_list_df = []
    else:
        dept_list_df = []
    dept_list = list(set(dept_list_db + dept_list_df))
    
    for dept in dept_list:
        if not Department.objects.filter(dept=dept).exists():
            Department.objects.create(dept=dept)

    # Lọc theo phòng ban nếu có
    if dept_order:
        if dept_perform:
            detail_revenue_groupby = detail_revenue_groupby[
                (detail_revenue_groupby['sd_makhoa_taichinh_order'] == dept_order) &
                (detail_revenue_groupby['sd_makhoa_taichinh'] == dept_perform)
            ]   
        else:
            detail_revenue_groupby = detail_revenue_groupby[
                detail_revenue_groupby['sd_makhoa_taichinh_order'] == dept_order
            ]
    elif dept_perform:
        detail_revenue_groupby = detail_revenue_groupby[
            detail_revenue_groupby['sd_makhoa_taichinh'] == dept_perform        ]
    
    return detail_revenue_groupby

def get_reconcile_revenue_by_dept_order_data(from_date, to_date, dept_order=None):
    # Lấy dữ liệu từ API
    revenue_series = call_api_revenue(from_date, to_date)['data']
    df_revenue = pd.DataFrame(revenue_series)
    
    # Tách dữ liệu theo điều kiện drug_retail
    df_revenue_except_drug_retail = df_revenue.query("drug_retail == 'N'")
    df_revenue_drug_retail = df_revenue.query("drug_retail == 'Y'")
    
    # Tạo danh sách các hft_id2 và tên cột tương ứng
    hft_mappings = {
        'DT001': 'tien_kham',
        'DT002': 'tien_giuong',
        'DT003': 'tien_cls',
        'DT004': 'tien_pttt',
        'DT005': 'tien_thuoc',
        'DT006': 'tien_vattu',
        'DT007': 'tien_thuoc_pm',
        'DT008': 'tien_vattu_pm',
        'DT009': 'tien_khac',
    }

    # Tạo DataFrame tổng hợp từng nhóm
    grouped_dataframes = []
    for hft_id, column_name in hft_mappings.items():
        df_filtered = df_revenue_except_drug_retail[df_revenue_except_drug_retail['hft_id2'] == hft_id]
        df_grouped = df_filtered.groupby(['kcb_class', 'price_type', 'object_type','sd_makhoa_taichinh_order', 'sd_makhoa_taichinh'])['revenue'] \
            .sum().reset_index().rename(columns={'revenue': column_name})
        grouped_dataframes.append(df_grouped)

    # Merge tất cả các DataFrame
    revenue_except_drug_retail = reduce(
        lambda left, right: pd.merge(left, right, on=['kcb_class', 'price_type', 'object_type','sd_makhoa_taichinh_order', 'sd_makhoa_taichinh'], how='outer'),
        grouped_dataframes
    )

    # Tổng hợp dữ liệu và nhóm theo phòng ban
    total_drug_retail = df_revenue_drug_retail.groupby(['kcb_class', 'price_type', 'object_type','sd_makhoa_taichinh_order', 'sd_makhoa_taichinh'])['revenue'].sum().reset_index().rename(columns={'revenue': 'drug_retail'})
    summary_revenue = pd.merge(revenue_except_drug_retail, total_drug_retail, on=['kcb_class', 'price_type', 'object_type','sd_makhoa_taichinh_order', 'sd_makhoa_taichinh'], how='outer')
    reconcile_revenue_by_dept_order = summary_revenue.groupby(
        ['sd_makhoa_taichinh_order', 'sd_makhoa_taichinh', 'kcb_class', 'price_type', 'object_type'], dropna=False
    ).sum().reset_index()

    reconcile_revenue_by_dept_order['kcb_class'] = reconcile_revenue_by_dept_order['kcb_class'].replace({1: 'Ngoại trú', 2: 'Nội trú'})
    reconcile_revenue_by_dept_order['price_type'] = reconcile_revenue_by_dept_order['price_type'].replace({1: 'Thông thường', 2: 'Theo yêu cầu'})
    reconcile_revenue_by_dept_order['object_type'] = reconcile_revenue_by_dept_order['object_type'].replace({1: 'BHYT', 2: 'Dịch vụ'})


    # Lọc theo phòng ban nếu có
    if dept_order:
        reconcile_revenue_by_dept_order = reconcile_revenue_by_dept_order[
            reconcile_revenue_by_dept_order['sd_makhoa_taichinh_order'] == dept_order
        ]

    return reconcile_revenue_by_dept_order

def get_revenue_reconciliation_data(from_date,to_date,selected_status=None):
    # Gọi API lấy dữ liệu
    data_sources = {
        'revenue': call_api_with_retry(call_api_revenue, from_date, to_date),
        'ar': call_api_with_retry(call_api_ar, from_date, to_date),
    }

    # Chuyển dữ liệu thành DataFrame
    df = {key: pd.DataFrame(value) if value else pd.DataFrame() for key, value in data_sources.items()}
    # Ép kiểu cột hfe_invoiceno sang string nếu tồn tại trong các bảng liên quan
    for key in ['revenue', 'ar']:
        if not df[key].empty and 'hfe_invoiceno' in df[key].columns:
            df[key]['hfe_invoiceno'] = df[key]['hfe_invoiceno'].astype(str)
    # Danh sách các mã `hft_id2` và tên cột tương ứng
    revenue_types = {
        'DT001': 'tien_kham',
        'DT002': 'tien_giuong',
        'DT003': 'tien_cls',
        'DT004': 'tien_pttt',
        'DT005': 'tien_thuoc',
        'DT006': 'tien_vattu',
        'DT007': 'tien_thuoc_pm',
        'DT008': 'tien_vattu_pm',
        'DT009': 'tien_khac',
    }

    # Hàm helper để tính tổng revenue theo nhóm
    def group_and_rename(df, hft_id2, new_column):
        filtered_df = df[df['hft_id2'] == hft_id2]
        return filtered_df.groupby(['hfe_invoiceno', 'hfe_docno_1'])['revenue'].sum().reset_index().rename(columns={'revenue': new_column})

    # Áp dụng cho từng loại revenue
    grouped_revenues = [group_and_rename(df['revenue'], hft_id, col_name) for hft_id, col_name in revenue_types.items()]

    # Gộp các DataFrame
    merged_df = grouped_revenues[0]
    for grp_df in grouped_revenues[1:]:
        merged_df = pd.merge(merged_df, grp_df, on=['hfe_invoiceno', 'hfe_docno_1'], how='outer')

    # Tính tổng revenue theo hóa đơn và gộp vào DataFrame
    df_revenue_total = df['revenue'].groupby(['hfe_invoiceno', 'hfe_docno_1'])['revenue'].sum().reset_index().rename(columns={'revenue': 'revenue_by_detail'})
    df_total_revenue_by_invoice = df['ar'].groupby(['hfe_invoiceno', 'hfe_docno_1'])['revenue'].sum().reset_index()

    merged_df = pd.merge(merged_df, df_revenue_total, on=['hfe_invoiceno', 'hfe_docno_1'], how='outer')
    merged_df = pd.merge(merged_df, df_total_revenue_by_invoice, on=['hfe_invoiceno', 'hfe_docno_1'], how='outer')

    # Tổng hợp dữ liệu cuối cùng
    revenue_reconciliation = merged_df.groupby(['hfe_docno_1'], dropna=False)[list(revenue_types.values()) + ['revenue_by_detail', 'revenue']].sum().reset_index()
    revenue_reconciliation['comparison_criteria'] = abs(revenue_reconciliation['revenue_by_detail'] - revenue_reconciliation['revenue']) <= 100

    # Lọc theo trạng thái nếu được chọn
    if selected_status is not None:
        revenue_reconciliation = revenue_reconciliation[revenue_reconciliation['comparison_criteria'] == selected_status]
    
    return revenue_reconciliation

def get_summary_deduction_data(from_date,to_date):
    deduction_series = call_api_deduction(from_date,to_date)['data']
    df_deduction = pd.DataFrame(deduction_series)

    # Tách dữ liệu theo điều kiện drug_retail
    df_deduction_except_drug_retail = df_deduction.query("drug_retail == 'N'")
    df_deduction_drug_retail = df_deduction.query("drug_retail == 'Y'")
    
    # Tạo danh sách các hft_id2 và tên cột tương ứng
    hft_mappings = {
        'DT001': 'tien_kham',
        'DT002': 'tien_giuong',
        'DT003': 'tien_cls',
        'DT004': 'tien_pttt',
        'DT005': 'tien_thuoc',
        'DT006': 'tien_vattu',
        'DT007': 'tien_thuoc_pm',
        'DT008': 'tien_vattu_pm',
        'DT009': 'tien_khac',
        }

    # Tạo DataFrame tổng hợp từng nhóm
    grouped_dataframes = []
    for hft_id, column_name in hft_mappings.items():
        df_filtered = df_deduction_except_drug_retail[df_deduction_except_drug_retail['hft_id2'] == hft_id]
        df_grouped = df_filtered.groupby(['kcb_class', 'price_type', 'object_type'])['revenue'] \
                            .sum().reset_index().rename(columns={'revenue': column_name})
        grouped_dataframes.append(df_grouped)

    df_total_deduction_except_drug_retail = reduce(lambda left, right: pd.merge(left, right, on=['kcb_class', 'price_type', 'object_type'], how='outer'), grouped_dataframes)

    # Thêm tổng doanh thu từ df_ar
    df_total_drug_retail = df_deduction_drug_retail.groupby(['kcb_class', 'price_type', 'object_type'])['revenue'].sum().reset_index().rename(columns={'revenue': 'drug_retail'})
    summary_deduction = pd.merge(df_total_deduction_except_drug_retail, df_total_drug_retail, on=['kcb_class', 'price_type', 'object_type'], how='outer')

    # Sắp xếp dữ liệu
    summary_deduction = summary_deduction.groupby(['kcb_class', 'price_type', 'object_type'], dropna=False).sum().reset_index()
    summary_deduction['kcb_class'] = summary_deduction['kcb_class'].replace({1: 'Ngoại trú', 2: 'Nội trú'})
    summary_deduction['price_type'] = summary_deduction['price_type'].replace({1: 'Thông thường', 2: 'Theo yêu cầu'})
    summary_deduction['object_type'] = summary_deduction['object_type'].replace({1: 'BHYT', 2: 'Dịch vụ'})
    return summary_deduction

def get_summary_deduction_by_dept_order_data(from_date, to_date, dept_order=None):
    # Lấy dữ liệu từ API
    deduction_series = call_api_with_retry(call_api_deduction, from_date, to_date)
    df_deduction = pd.DataFrame(deduction_series)
    
    # Tách dữ liệu theo điều kiện drug_retail
    df_deduction_except_drug_retail = df_deduction.query("drug_retail == 'N'")
    df_deduction_drug_retail = df_deduction.query("drug_retail == 'Y'")
    
    # Tạo danh sách các hft_id2 và tên cột tương ứng
    hft_mappings = {
        'DT001': 'tien_kham',
        'DT002': 'tien_giuong',
        'DT003': 'tien_cls',
        'DT004': 'tien_pttt',
        'DT005': 'tien_thuoc',
        'DT006': 'tien_vattu',
        'DT007': 'tien_thuoc_pm',
        'DT008': 'tien_vattu_pm',
        'DT009': 'tien_khac',
    }

    # Tạo DataFrame tổng hợp từng nhóm
    grouped_dataframes = []
    for hft_id, column_name in hft_mappings.items():
        df_filtered = df_deduction_except_drug_retail[df_deduction_except_drug_retail['hft_id2'] == hft_id]
        df_grouped = df_filtered.groupby(['kcb_class', 'price_type', 'object_type','sd_makhoa_taichinh_order'])['revenue'] \
            .sum().reset_index().rename(columns={'revenue': column_name})
        grouped_dataframes.append(df_grouped)

    # Merge tất cả các DataFrame
    deduction_except_drug_retail = reduce(
        lambda left, right: pd.merge(left, right, on=['kcb_class', 'price_type', 'object_type','sd_makhoa_taichinh_order'], how='outer'),
        grouped_dataframes
    )

    # Tổng hợp dữ liệu và nhóm theo phòng ban
    total_drug_retail = df_deduction_drug_retail.groupby(['kcb_class', 'price_type', 'object_type','sd_makhoa_taichinh_order'])['revenue'].sum().reset_index().rename(columns={'revenue': 'drug_retail'})
    summary_deduction = pd.merge(deduction_except_drug_retail, total_drug_retail, on=['kcb_class', 'price_type', 'object_type','sd_makhoa_taichinh_order'], how='outer')
    summary_deduction_by_dept_order = summary_deduction.groupby(
        ['sd_makhoa_taichinh_order', 'kcb_class', 'price_type', 'object_type'], dropna=False
    ).sum().reset_index()
    summary_deduction_by_dept_order['kcb_class'] = summary_deduction_by_dept_order['kcb_class'].replace({1: 'Ngoại trú', 2: 'Nội trú'})
    summary_deduction_by_dept_order['price_type'] = summary_deduction_by_dept_order['price_type'].replace({1: 'Thông thường', 2: 'Theo yêu cầu'})
    summary_deduction_by_dept_order['object_type'] = summary_deduction_by_dept_order['object_type'].replace({1: 'BHYT', 2: 'Dịch vụ'})

    # Lọc theo phòng ban nếu có
    if dept_order:
        summary_deduction_by_dept_order = summary_deduction_by_dept_order[
            summary_deduction_by_dept_order['sd_makhoa_taichinh_order'] == dept_order
        ]

    return summary_deduction_by_dept_order

def get_reconcile_deduction_by_dept_order_data(from_date, to_date, dept_order=None):
    # Lấy dữ liệu từ API
    deduction_series = call_api_deduction(from_date, to_date)['data']
    df_deduction = pd.DataFrame(deduction_series)
    
    # Tách dữ liệu theo điều kiện drug_retail
    df_deduction_except_drug_retail = df_deduction.query("drug_retail == 'N'")
    df_deduction_drug_retail = df_deduction.query("drug_retail == 'Y'")
    
    # Tạo danh sách các hft_id2 và tên cột tương ứng
    hft_mappings = {
        'DT001': 'tien_kham',
        'DT002': 'tien_giuong',
        'DT003': 'tien_cls',
        'DT004': 'tien_pttt',
        'DT005': 'tien_thuoc',
        'DT006': 'tien_vattu',
        'DT007': 'tien_thuoc_pm',
        'DT008': 'tien_vattu_pm',
        'DT009': 'tien_khac',
    }

    # Tạo DataFrame tổng hợp từng nhóm
    grouped_dataframes = []
    for hft_id, column_name in hft_mappings.items():
        df_filtered = df_deduction_except_drug_retail[df_deduction_except_drug_retail['hft_id2'] == hft_id]
        df_grouped = df_filtered.groupby(['kcb_class', 'price_type', 'object_type','sd_makhoa_taichinh_order', 'sd_makhoa_taichinh'])['revenue'] \
            .sum().reset_index().rename(columns={'revenue': column_name})
        grouped_dataframes.append(df_grouped)

    # Merge tất cả các DataFrame
    deduction_except_drug_retail = reduce(
        lambda left, right: pd.merge(left, right, on=['kcb_class', 'price_type', 'object_type','sd_makhoa_taichinh_order', 'sd_makhoa_taichinh'], how='outer'),
        grouped_dataframes
    )

    # Tổng hợp dữ liệu và nhóm theo phòng ban
    total_drug_retail = df_deduction_drug_retail.groupby(['kcb_class', 'price_type', 'object_type','sd_makhoa_taichinh_order', 'sd_makhoa_taichinh'])['revenue'].sum().reset_index().rename(columns={'revenue': 'drug_retail'})
    summary_deduction = pd.merge(deduction_except_drug_retail, total_drug_retail, on=['kcb_class', 'price_type', 'object_type','sd_makhoa_taichinh_order', 'sd_makhoa_taichinh'], how='outer')
    reconcile_deduction_by_dept_order = summary_deduction.groupby(
        ['sd_makhoa_taichinh_order', 'sd_makhoa_taichinh', 'kcb_class', 'price_type', 'object_type'], dropna=False
    ).sum().reset_index()

    reconcile_deduction_by_dept_order['kcb_class'] = reconcile_deduction_by_dept_order['kcb_class'].replace({1: 'Ngoại trú', 2: 'Nội trú'})
    reconcile_deduction_by_dept_order['price_type'] = reconcile_deduction_by_dept_order['price_type'].replace({1: 'Thông thường', 2: 'Theo yêu cầu'})
    reconcile_deduction_by_dept_order['object_type'] = reconcile_deduction_by_dept_order['object_type'].replace({1: 'BHYT', 2: 'Dịch vụ'})


    # Lọc theo phòng ban nếu có
    if dept_order:
        reconcile_deduction_by_dept_order = reconcile_deduction_by_dept_order[
            reconcile_deduction_by_dept_order['sd_makhoa_taichinh_order'] == dept_order
        ]

    return reconcile_deduction_by_dept_order

def get_detail_deduction_groupby_data(from_date,to_date,dept_order=None,dept_perform=None):
    detail_deduction_series = call_api_detail_deduction(from_date,to_date)['data']
    df_detail_deduction = pd.DataFrame(detail_deduction_series)
    detail_deduction_groupby = df_detail_deduction.groupby(['kcb_class','price_type','object_type','hft_name','hfe_group','hfe_itemid','hfe_desc','sd_makhoa_taichinh_order','sd_makhoa_taichinh','hfe_unit'],dropna=False)[['hfe_quantity','revenue']].sum().sort_values(by=['kcb_class','price_type','object_type']).reset_index()
    detail_deduction_groupby['kcb_class'] = detail_deduction_groupby['kcb_class'].replace({1: 'Ngoại trú', 2: 'Nội trú'})
    detail_deduction_groupby['price_type'] = detail_deduction_groupby['price_type'].replace({1: 'Thông thường', 2: 'Theo yêu cầu'})
    detail_deduction_groupby['object_type'] = detail_deduction_groupby['object_type'].replace({1: 'BHYT', 2: 'Dịch vụ'})
    # Lấy danh sách phòng ban từ cơ sở dữ liệu và dữ liệu API
    dept_list_db = list(Department.objects.values_list('dept', flat=True))
    if detail_deduction_groupby is not None and not detail_deduction_groupby.empty:
        if 'sd_makhoa_taichinh' in detail_deduction_groupby.columns:
            dept_list_df = detail_deduction_groupby['sd_makhoa_taichinh'].dropna().unique().tolist()
        else:
            dept_list_df = []
    else:
        dept_list_df = []
    dept_list = list(set(dept_list_db + dept_list_df))
    
    for dept in dept_list:
        if not Department.objects.filter(dept=dept).exists():
            Department.objects.create(dept=dept)

    # Lọc theo phòng ban nếu có
    if dept_order:
        if dept_perform:
            detail_deduction_groupby = detail_deduction_groupby[
                (detail_deduction_groupby['sd_makhoa_taichinh_order'] == dept_order) &
                (detail_deduction_groupby['sd_makhoa_taichinh'] == dept_perform)
            ]   
        else:
            detail_deduction_groupby = detail_deduction_groupby[
                detail_deduction_groupby['sd_makhoa_taichinh_order'] == dept_order
            ]
    elif dept_perform:
        detail_deduction_groupby = detail_deduction_groupby[
            detail_deduction_groupby['sd_makhoa_taichinh'] == dept_perform        ]
    
    return detail_deduction_groupby

def get_drug_retail_revenue_data(from_date,to_date):
    
    revenue_series = call_api_revenue(from_date,to_date)['data']
    df_revenue = pd.DataFrame(revenue_series)
    df_drug_retail_revenue = df_revenue[(df_revenue['drug_retail'] == 'Y')]

    # Tạo danh sách các hft_id2 và tên cột tương ứng
    hft_mappings = {
        'DT001': 'tien_kham',
        'DT002': 'tien_giuong',
        'DT003': 'tien_cls',
        'DT004': 'tien_pttt',
        'DT005': 'tien_thuoc',
        'DT006': 'tien_vattu',
        'DT007': 'tien_thuoc_pm',
        'DT008': 'tien_vattu_pm',
        'DT009': 'tien_khac',
        }

    # Tạo DataFrame tổng hợp từng nhóm
    grouped_dataframes = []
    for hft_id2, column_name in hft_mappings.items():
        df_filtered = df_drug_retail_revenue[df_drug_retail_revenue['hft_id2'] == hft_id2]
        df_grouped = df_filtered.groupby(['kcb_class', 'price_type', 'object_type','drug_retail'])['revenue'] \
                             .sum().reset_index().rename(columns={'revenue': column_name})
        grouped_dataframes.append(df_grouped)

    # Merge tất cả các DataFrame
    drug_retail_revenue_groupby = reduce(lambda left, right: pd.merge(left, right, on=['kcb_class', 'price_type', 'object_type','drug_retail'], how='outer'), grouped_dataframes)

    # Sắp xếp dữ liệu
    drug_retail_cogs = df_drug_retail_revenue.groupby(['kcb_class', 'price_type', 'object_type','drug_retail'], dropna=False)['cogs_drug_retail'].sum().reset_index()
    drug_retail_revenue_groupby = drug_retail_revenue_groupby.groupby(['kcb_class', 'price_type', 'object_type','drug_retail'], dropna=False).sum().reset_index()
    drug_retail_revenue = pd.merge(drug_retail_cogs, drug_retail_revenue_groupby, on=['kcb_class', 'price_type', 'object_type'], how='outer')
    drug_retail_revenue['kcb_class'] = drug_retail_revenue['kcb_class'].replace({1: 'Ngoại trú', 2: 'Nội trú'})
    drug_retail_revenue['price_type'] = drug_retail_revenue['price_type'].replace({1: 'Thông thường', 2: 'Theo yêu cầu'})
    drug_retail_revenue['object_type'] = drug_retail_revenue['object_type'].replace({1: 'BHYT', 2: 'Dịch vụ'})
    return drug_retail_revenue

def get_functional_food_revenue_data(from_date, to_date):        
    # Gọi API và tạo DataFrame
    revenue_series = call_api_revenue(from_date, to_date)['data']
    df_revenue = pd.DataFrame(revenue_series)

    # Kiểm tra và thêm cột nếu thiếu
    if 'drug_retail' not in df_revenue.columns:
        df_revenue['drug_retail'] = None
    if 'hft_id' not in df_revenue.columns:
        df_revenue['hft_id'] = None

    # Tạo danh sách các hft_id2 và tên cột tương ứng
    hft_mappings = {
        'DT001': 'tien_kham',
        'DT002': 'tien_giuong',
        'DT003': 'tien_cls',
        'DT004': 'tien_pttt',
        'DT005': 'tien_thuoc',
        'DT006': 'tien_vattu',
        'DT007': 'tien_thuoc_pm',
        'DT008': 'tien_vattu_pm',
        'DT009': 'tien_khac',
    }

    # Tạo DataFrame tổng hợp từng nhóm
    grouped_dataframes = []
    for hft_id2, column_name in hft_mappings.items():
        df_filtered = df_revenue[df_revenue['hft_id2'] == hft_id2]
        df_grouped = (
        df_filtered.groupby(['kcb_class', 'price_type', 'object_type', 'drug_retail', 'hft_id'])['revenue']
            .sum()
            .reset_index()
            .rename(columns={'revenue': column_name})
        )
        grouped_dataframes.append(df_grouped)

    # Merge tất cả các DataFrame
    functional_food_revenue = reduce(
        lambda left, right: pd.merge(
            left, right, on=['kcb_class', 'price_type', 'object_type', 'drug_retail', 'hft_id'], how='outer'
        ),
        grouped_dataframes,
    )

    # Kiểm tra sự tồn tại của các cột trước khi lọc
    if 'drug_retail' in functional_food_revenue.columns and 'hft_id' in functional_food_revenue.columns:
        functional_food_revenue = functional_food_revenue[
            (functional_food_revenue['drug_retail'] == 'Y') &
            (functional_food_revenue['hft_id'] == 2002)
        ]

    # Gộp dữ liệu và sắp xếp
    functional_food_revenue = (
        functional_food_revenue.groupby(['kcb_class', 'price_type', 'object_type', 'drug_retail', 'hft_id'], dropna=False)
        .sum()
        .reset_index()
    )
    functional_food_revenue['kcb_class'] = functional_food_revenue['kcb_class'].replace({1: 'Ngoại trú', 2: 'Nội trú'})
    functional_food_revenue['price_type'] = functional_food_revenue['price_type'].replace({1: 'Thông thường', 2: 'Theo yêu cầu'})
    functional_food_revenue['object_type'] = functional_food_revenue['object_type'].replace({1: 'BHYT', 2: 'Dịch vụ'})
    return functional_food_revenue

def get_drug_retail_deduction_data(from_date,to_date):
    
    deduction_series = call_api_deduction(from_date,to_date)['data']
    df_deduction = pd.DataFrame(deduction_series)
    df_drug_retail_deduction = df_deduction[(df_deduction['drug_retail'] == 'Y')]

    # Tạo danh sách các hft_id2 và tên cột tương ứng
    hft_mappings = {
        'DT001': 'tien_kham',
        'DT002': 'tien_giuong',
        'DT003': 'tien_cls',
        'DT004': 'tien_pttt',
        'DT005': 'tien_thuoc',
        'DT006': 'tien_vattu',
        'DT007': 'tien_thuoc_pm',
        'DT008': 'tien_vattu_pm',
        'DT009': 'tien_khac',
        }

    # Tạo DataFrame tổng hợp từng nhóm
    grouped_dataframes = []
    for hft_id2, column_name in hft_mappings.items():
        df_filtered = df_drug_retail_deduction[df_drug_retail_deduction['hft_id2'] == hft_id2]
        df_grouped = df_filtered.groupby(['kcb_class', 'price_type', 'object_type','drug_retail'])['revenue'] \
                             .sum().reset_index().rename(columns={'revenue': column_name})
        grouped_dataframes.append(df_grouped)

    # Merge tất cả các DataFrame
    drug_retail_deduction_groupby = reduce(lambda left, right: pd.merge(left, right, on=['kcb_class', 'price_type', 'object_type','drug_retail'], how='outer'), grouped_dataframes)

    # Sắp xếp dữ liệu
    drug_retail_cogs = df_drug_retail_deduction.groupby(['kcb_class', 'price_type', 'object_type','drug_retail'], dropna=False)['cogs_drug_retail'].sum().reset_index()
    drug_retail_deduction_groupby = drug_retail_deduction_groupby.groupby(['kcb_class', 'price_type', 'object_type','drug_retail'], dropna=False).sum().reset_index()
    drug_retail_deduction = pd.merge(drug_retail_cogs, drug_retail_deduction_groupby, on=['kcb_class', 'price_type', 'object_type'], how='outer')
    drug_retail_deduction['kcb_class'] = drug_retail_deduction['kcb_class'].replace({1: 'Ngoại trú', 2: 'Nội trú'})
    drug_retail_deduction['price_type'] = drug_retail_deduction['price_type'].replace({1: 'Thông thường', 2: 'Theo yêu cầu'})
    drug_retail_deduction['object_type'] = drug_retail_deduction['object_type'].replace({1: 'BHYT', 2: 'Dịch vụ'})
    return drug_retail_deduction

def get_drug_retail_revenue_detail_data(from_date,to_date):
    
    revenue_series = call_api_revenue(from_date,to_date)['data']
    df_revenue = pd.DataFrame(revenue_series)

    # Tạo danh sách các hft_id2 và tên cột tương ứng
    hft_mappings = {
        'DT001': 'tien_kham',
        'DT002': 'tien_giuong',
        'DT003': 'tien_cls',
        'DT004': 'tien_pttt',
        'DT005': 'tien_thuoc',
        'DT006': 'tien_vattu',
        'DT007': 'tien_thuoc_pm',
        'DT008': 'tien_vattu_pm',
        'DT009': 'tien_khac',
        }

    # Tạo DataFrame tổng hợp từng nhóm
    grouped_dataframes = []
    for hft_id2, column_name in hft_mappings.items():
        df_filtered = df_revenue[df_revenue['hft_id2'] == hft_id2]
        df_grouped = df_filtered.groupby(['kcb_class', 'price_type', 'object_type','drug_retail'])['revenue'] \
                             .sum().reset_index().rename(columns={'revenue': column_name})
        grouped_dataframes.append(df_grouped)

    # Merge tất cả các DataFrame
    drug_retail_revenue = reduce(lambda left, right: pd.merge(left, right, on=['kcb_class', 'price_type', 'object_type','drug_retail'], how='outer'), grouped_dataframes)

    # Sắp xếp dữ liệu
    drug_retail_revenue = drug_retail_revenue[(drug_retail_revenue['drug_retail'] == 'Y')]
    drug_retail_revenue = drug_retail_revenue.groupby(['kcb_class', 'price_type', 'object_type','drug_retail'], dropna=False).sum().reset_index()
    drug_retail_revenue['kcb_class'] = drug_retail_revenue['kcb_class'].replace({1: 'Ngoại trú', 2: 'Nội trú'})
    drug_retail_revenue['price_type'] = drug_retail_revenue['price_type'].replace({1: 'Thông thường', 2: 'Theo yêu cầu'})
    drug_retail_revenue['object_type'] = drug_retail_revenue['object_type'].replace({1: 'BHYT', 2: 'Dịch vụ'})
    return drug_retail_revenue

def get_summary_cost_in_package_by_dept_data(from_date, to_date, dept_perform=None):
    # Lấy dữ liệu từ API
    revenue_series = call_api_with_retry(call_api_revenue, from_date, to_date)
    df_revenue = pd.DataFrame(revenue_series)

    # Thay thế giá trị NaN trong 'sd_makhoa_taichinh' để giữ lại khi groupby
    df_revenue['sd_makhoa_taichinh'] = df_revenue['sd_makhoa_taichinh'].fillna("Không xác định")

    # Tách dữ liệu theo điều kiện drug_retail
    df_revenue_except_drug_retail = df_revenue.query("drug_retail == 'N'")
    df_revenue_drug_retail = df_revenue.query("drug_retail == 'Y'")

    # Tạo danh sách các hft_id2 và tên cột tương ứng
    hft_mappings = {
        'DT001': 'tien_kham',
        'DT002': 'tien_giuong',
        'DT003': 'tien_cls',
        'DT004': 'tien_pttt',
        'DT005': 'tien_thuoc',
        'DT006': 'tien_vattu',
        'DT007': 'tien_thuoc_pm',
        'DT008': 'tien_vattu_pm',
        'DT009': 'tien_khac',
    }

    # Tạo danh sách DataFrame cho từng nhóm hft_id2
    grouped_dataframes = [
        df_revenue_except_drug_retail.query(f"hft_id2 == '{hft_id}'")
        .groupby(['kcb_class', 'price_type', 'object_type','sd_makhoa_taichinh'], dropna=False)['cost_in_package']
        .sum()
        .reset_index()
        .rename(columns={'cost_in_package': column_name})
        for hft_id, column_name in hft_mappings.items()
    ]

    # Gộp tất cả các DataFrame theo 'sd_makhoa_taichinh'
    summary_cost_in_package_except_drug_retail = reduce(
        lambda left, right: pd.merge(left, right, on=['kcb_class', 'price_type', 'object_type','sd_makhoa_taichinh'], how='outer'),
        grouped_dataframes
    )

    # Tổng hợp doanh thu bán lẻ thuốc và tổng chi phí trong gói
    df_total_drug_retail = df_revenue_drug_retail.groupby(['kcb_class', 'price_type', 'object_type','sd_makhoa_taichinh'], dropna=False)['revenue'].sum().reset_index().rename(columns={'revenue': 'drug_retail'})
    df_total_revenue = df_revenue.groupby(['kcb_class', 'price_type', 'object_type','sd_makhoa_taichinh'], dropna=False)['revenue'].sum().reset_index()

    # Gộp tất cả vào bảng chính
    summary_cost_in_package = summary_cost_in_package_except_drug_retail
    for df_merge in [df_total_drug_retail, df_total_revenue]:
        summary_cost_in_package = summary_cost_in_package.merge(df_merge, on=['kcb_class', 'price_type', 'object_type','sd_makhoa_taichinh'], how='outer')

    # Nhóm theo phòng ban, giữ lại NaN (nếu có)
    summary_cost_in_package_by_dept = summary_cost_in_package.groupby(['kcb_class', 'price_type', 'object_type','sd_makhoa_taichinh'], dropna=False).sum().reset_index()
    summary_cost_in_package_by_dept['kcb_class'] = summary_cost_in_package_by_dept['kcb_class'].replace({1: 'Ngoại trú', 2: 'Nội trú'})
    summary_cost_in_package_by_dept['price_type'] = summary_cost_in_package_by_dept['price_type'].replace({1: 'Thông thường', 2: 'Theo yêu cầu'})
    summary_cost_in_package_by_dept['object_type'] = summary_cost_in_package_by_dept['object_type'].replace({1: 'BHYT', 2: 'Dịch vụ'})
    
    # Lọc theo phòng ban nếu có
    if dept_perform:
        summary_cost_in_package_by_dept = summary_cost_in_package_by_dept.query(f"sd_makhoa_taichinh == '{dept_perform}'")

    return summary_cost_in_package_by_dept

def get_summary_exam_revenue_data(from_date,to_date):
    exam_revenue_series = call_api_exam_revenue(from_date,to_date)['data']
    df_exam_revenue = pd.DataFrame(exam_revenue_series)

    # Tách dữ liệu theo điều kiện drug_retail
    df_exam_revenue_except_drug_retail = df_exam_revenue.query("drug_retail == 'N'")
    df_exam_revenue_drug_retail = df_exam_revenue.query("drug_retail == 'Y'")
    
    # Thay NaN thành 'NULL' trước khi merge để tránh mất dòng
    for df in [df_exam_revenue_except_drug_retail, df_exam_revenue_drug_retail]:
        df['hec_no'] = df['hec_no'].fillna('NULL')
        
    # Tạo danh sách các hft_id2 và tên cột tương ứng
    hft_mappings = {
        'DT001': 'tien_kham',
        'DT002': 'tien_giuong',
        'DT003': 'tien_cls',
        'DT004': 'tien_pttt',
        'DT005': 'tien_thuoc',
        'DT006': 'tien_vattu',
        'DT007': 'tien_thuoc_pm',
        'DT008': 'tien_vattu_pm',
        'DT009': 'tien_khac',
        }

    # Tạo DataFrame tổng hợp từng nhóm
    grouped_dataframes = []
    for hft_id, column_name in hft_mappings.items():
        df_filtered = df_exam_revenue_except_drug_retail[df_exam_revenue_except_drug_retail['hft_id2'] == hft_id]
        df_grouped = df_filtered.groupby(['kcb_class', 'price_type', 'object_type','hfe_company2_id','com_name','hec_no'])['revenue'] \
                            .sum().reset_index().rename(columns={'revenue': column_name})
        grouped_dataframes.append(df_grouped)

    df_total_exam_revenue_except_drug_retail = reduce(lambda left, right: pd.merge(left, right, on=['kcb_class', 'price_type', 'object_type','hfe_company2_id','com_name','hec_no'], how='outer'), grouped_dataframes)

    # Thêm tổng doanh thu từ df_ar
    df_total_drug_retail = df_exam_revenue_drug_retail.groupby(['kcb_class', 'price_type', 'object_type','hfe_company2_id','com_name','hec_no'])['revenue'].sum().reset_index().rename(columns={'revenue': 'drug_retail'})
    summary_exam_revenue = pd.merge(df_total_exam_revenue_except_drug_retail, df_total_drug_retail, on=['kcb_class', 'price_type', 'object_type','hfe_company2_id','com_name','hec_no'], how='outer')

    # Sắp xếp dữ liệu
    summary_exam_revenue = summary_exam_revenue.groupby(['kcb_class', 'price_type', 'object_type','hfe_company2_id','com_name','hec_no'], dropna=False).sum().reset_index()
    summary_exam_revenue['kcb_class'] = summary_exam_revenue['kcb_class'].replace({1: 'Ngoại trú', 2: 'Nội trú'})
    summary_exam_revenue['price_type'] = summary_exam_revenue['price_type'].replace({1: 'Thông thường', 2: 'Theo yêu cầu'})
    summary_exam_revenue['object_type'] = summary_exam_revenue['object_type'].replace({1: 'BHYT', 2: 'Dịch vụ'})
    return summary_exam_revenue

def get_summary_exam_revenue_data_by_patient(from_date,to_date):
    exam_revenue_series = call_api_exam_revenue(from_date,to_date)['data']
    df_exam_revenue = pd.DataFrame(exam_revenue_series)

    # Tách dữ liệu theo điều kiện drug_retail
    df_exam_revenue_except_drug_retail = df_exam_revenue.query("drug_retail == 'N'")
    df_exam_revenue_drug_retail = df_exam_revenue.query("drug_retail == 'Y'")
    
    # Thay NaN thành 'NULL' trước khi merge để tránh mất dòng
    for df in [df_exam_revenue_except_drug_retail, df_exam_revenue_drug_retail]:
        df['hec_no'] = df['hec_no'].fillna('NULL')
        
    # Tạo danh sách các hft_id2 và tên cột tương ứng
    hft_mappings = {
        'DT001': 'tien_kham',
        'DT002': 'tien_giuong',
        'DT003': 'tien_cls',
        'DT004': 'tien_pttt',
        'DT005': 'tien_thuoc',
        'DT006': 'tien_vattu',
        'DT007': 'tien_thuoc_pm',
        'DT008': 'tien_vattu_pm',
        'DT009': 'tien_khac',
        }

    # Tạo DataFrame tổng hợp từng nhóm
    grouped_dataframes = []
    for hft_id, column_name in hft_mappings.items():
        df_filtered = df_exam_revenue_except_drug_retail[df_exam_revenue_except_drug_retail['hft_id2'] == hft_id]
        df_grouped = df_filtered.groupby(['kcb_class', 'price_type', 'object_type','hfe_company2_id','com_name','hec_no','hfe_docno_1','hp_name'])['revenue'] \
                            .sum().reset_index().rename(columns={'revenue': column_name})
        grouped_dataframes.append(df_grouped)

    df_total_exam_revenue_except_drug_retail = reduce(lambda left, right: pd.merge(left, right, on=['kcb_class', 'price_type', 'object_type','hfe_company2_id','com_name','hec_no','hfe_docno_1','hp_name'], how='outer'), grouped_dataframes)

    # Thêm tổng doanh thu từ df_ar
    df_total_drug_retail = df_exam_revenue_drug_retail.groupby(['kcb_class', 'price_type', 'object_type','hfe_company2_id','com_name','hec_no','hfe_docno_1','hp_name'])['revenue'].sum().reset_index().rename(columns={'revenue': 'drug_retail'})
    summary_exam_revenue = pd.merge(df_total_exam_revenue_except_drug_retail, df_total_drug_retail, on=['kcb_class', 'price_type', 'object_type','hfe_company2_id','com_name','hec_no','hfe_docno_1','hp_name'], how='outer')

    # Sắp xếp dữ liệu
    summary_exam_revenue = summary_exam_revenue.groupby(['kcb_class', 'price_type', 'object_type','hfe_company2_id','com_name','hec_no','hfe_docno_1','hp_name'], dropna=False).sum().reset_index()
    summary_exam_revenue['kcb_class'] = summary_exam_revenue['kcb_class'].replace({1: 'Ngoại trú', 2: 'Nội trú'})
    summary_exam_revenue['price_type'] = summary_exam_revenue['price_type'].replace({1: 'Thông thường', 2: 'Theo yêu cầu'})
    summary_exam_revenue['object_type'] = summary_exam_revenue['object_type'].replace({1: 'BHYT', 2: 'Dịch vụ'})
    return summary_exam_revenue

def get_detail_inv_import_data(from_date, to_date, storage_ids):
    # Gọi API, lấy dữ liệu chi tiết nhập kho
    response = call_api_detail_inv_import(from_date, to_date, storage_ids)
    detail_inv_import_series = response.get('data', [])
    df_detail_inv_import = pd.DataFrame(detail_inv_import_series)

    # ----------------------
    # Cập nhật bảng Storage
    # ----------------------

    # Lấy danh sách storage_id đã có trong DB
    storage_list_db = list(Storage.objects.values_list('storage_id', flat=True))

    # Lấy từ API (DataFrame)
    if not df_detail_inv_import.empty and {'stock_import', 'stock_name'}.issubset(df_detail_inv_import.columns):
        # Lọc các cặp stock_import - stock_name (loại bỏ NA)
        storage_df = df_detail_inv_import[['stock_import', 'stock_name']].dropna()
        storage_df = storage_df.drop_duplicates()
        # Đảm bảo storage_id là kiểu int (nếu có thể)
        storage_df['stock_import'] = storage_df['stock_import'].astype(int, errors='ignore')
        storage_dict = storage_df.set_index('stock_import')['stock_name'].to_dict()
    else:
        storage_dict = {}

    # Hợp nhất danh sách storage_id
    all_storage_ids = set(storage_list_db).union(storage_dict.keys())

    for storage_id in all_storage_ids:
        storage_name = storage_dict.get(storage_id, "")

        # Nếu chưa tồn tại => tạo mới
        storage_obj = Storage.objects.filter(storage_id=storage_id).first()
        if not storage_obj:
            Storage.objects.create(storage_id=storage_id, storage_name=storage_name)
        else:
            # Nếu tồn tại nhưng chưa có tên => cập nhật
            if (not storage_obj.storage_name or storage_obj.storage_name.strip() == "") and storage_name:
                storage_obj.storage_name = storage_name
                storage_obj.save()
     # Kiểm tra và định dạng lại các cột ngày
    for col in ['transaction_date', 'invoicedate', 'signeddate', 'expdate' ]:
        if col in df_detail_inv_import.columns:
            df_detail_inv_import[col] = pd.to_datetime(
                df_detail_inv_import[col], errors='coerce'
            ).dt.strftime('%d-%m-%Y')  # Định dạng lại: YYYY-MM-DD

    return df_detail_inv_import

def get_detail_inv_export_data(from_date, to_date, storage_ids):
    # Gọi API, lấy dữ liệu chi tiết nhập kho
    response = call_api_detail_inv_export(from_date, to_date, storage_ids)
    detail_inv_export_series = response.get('data', [])
    df_detail_inv_export = pd.DataFrame(detail_inv_export_series)
    
    # Nếu có dữ liệu, xử lý định dạng
    if not df_detail_inv_export.empty:
        # Định dạng ngày tháng
        for date_col in ['transaction_date', 'receiptdate', 'expdate']:
            if date_col in df_detail_inv_export.columns:
                df_detail_inv_export[date_col] = pd.to_datetime(
                    df_detail_inv_export[date_col], errors='coerce'
                ).dt.strftime('%d-%m-%Y')

        # Định dạng các trường số nguyên
        for int_col in ['docno', 'invoiceno']:
            if int_col in df_detail_inv_export.columns:
                df_detail_inv_export[int_col] = pd.to_numeric(
                    df_detail_inv_export[int_col], errors='coerce'
                ).astype('Int64')  # Hỗ trợ cả NaN
    return df_detail_inv_export

def get_detail_inv_export_PDT_data(from_date, to_date, storage_ids):
    # Gọi API, lấy dữ liệu chi tiết nhập kho
    response = call_api_detail_inv_export_PDT(from_date, to_date, storage_ids)
    detail_inv_export_PDT_series = response.get('data', [])
    df_detail_inv_export_PDT = pd.DataFrame(detail_inv_export_PDT_series)
    # Nếu có dữ liệu, xử lý định dạng
    if not df_detail_inv_export_PDT.empty:
        # Định dạng ngày tháng
        for date_col in ['transaction_date', 'receiptdate']:
            if date_col in df_detail_inv_export_PDT.columns:
                df_detail_inv_export_PDT[date_col] = pd.to_datetime(
                    df_detail_inv_export_PDT[date_col], errors='coerce'
                ).dt.strftime('%d-%m-%Y')

        # Định dạng các trường số nguyên
        for int_col in ['docno', 'invoiceno']:
            if int_col in df_detail_inv_export_PDT.columns:
                df_detail_inv_export_PDT[int_col] = pd.to_numeric(
                    df_detail_inv_export_PDT[int_col], errors='coerce'
                ).astype('Int64')  # Hỗ trợ cả NaN
    return df_detail_inv_export_PDT
    