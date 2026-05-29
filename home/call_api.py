import requests
from collections import defaultdict
from datetime import datetime
import pandas as pd

#report_period = {"fromdate": "2024-09-24",
#        "todate": "2024-09-24"}
def call_api_invoice_receipt(from_date,to_date):
    url = "http://10.0.0.72:108/api/v1"
    
    # Các tham số truy vấn
    params = {
        'resource': 'api_DanhSachPhieuThuDichVu',
        'method': 'select'
    }
    report_period = {"fromdate": from_date,
            "todate": to_date}
    # Nếu cần gửi tiêu đề (headers) cho yêu cầu, bạn có thể thêm vào đây
    headers = {
        'Content-Type': 'application/json'  # Định dạng JSON cho body
    }
    
    try:
        # Gửi yêu cầu POST
        response = requests.post(url, params=params, json=report_period, headers=headers)
        response.raise_for_status()  # Kiểm tra lỗi HTTP
        
        # Trả về dữ liệu JSON nếu yêu cầu thành công
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {e}")
        return None

def call_api_refund(from_date,to_date):
    url = "http://10.0.0.72:108/api/v1"
    
    # Các tham số truy vấn
    params = {
        'resource': 'api_DanhSachPhieuChiTra',
        'method': 'select'
    }
    report_period = {"fromdate": from_date,
            "todate": to_date}
    # Nếu cần gửi tiêu đề (headers) cho yêu cầu, bạn có thể thêm vào đây
    headers = {
        'Content-Type': 'application/json'  # Định dạng JSON cho body
    }
    
    try:
        # Gửi yêu cầu POST
        response = requests.post(url, params=params, json=report_period, headers=headers)
        response.raise_for_status()  # Kiểm tra lỗi HTTP
        
        # Trả về dữ liệu JSON nếu yêu cầu thành công
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {e}")
        return None

def call_api_deposit(from_date,to_date):
    url = "http://10.0.0.72:108/api/v1"
    
    # Các tham số truy vấn
    params = {
        'resource': 'api_DanhSachPhieuThuTamUng',
        'method': 'select'
    }
    report_period = {"fromdate": from_date,
            "todate": to_date}
    # Nếu cần gửi tiêu đề (headers) cho yêu cầu, bạn có thể thêm vào đây
    headers = {
        'Content-Type': 'application/json'  # Định dạng JSON cho body
    }
    
    try:
        # Gửi yêu cầu POST
        response = requests.post(url, params=params, json=report_period, headers=headers)
        response.raise_for_status()  # Kiểm tra lỗi HTTP
        
        # Trả về dữ liệu JSON nếu yêu cầu thành công
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {e}")
        return None

def call_api_revenue(from_date,to_date):
    url = "http://10.0.0.72:108/api/v1"
    
    # Các tham số truy vấn
    params = {
        'resource': 'api_DoanhThu',
        'method': 'select'
    }
    report_period = {"fromdate": from_date,
            "todate": to_date}
    # Nếu cần gửi tiêu đề (headers) cho yêu cầu, bạn có thể thêm vào đây
    headers = {
        'Content-Type': 'application/json'  # Định dạng JSON cho body
    }
    
    try:
        # Gửi yêu cầu POST
        response = requests.post(url, params=params, json=report_period, headers=headers)
        response.raise_for_status()  # Kiểm tra lỗi HTTP
        
        # Trả về dữ liệu JSON nếu yêu cầu thành công
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {e}")
        return None

def call_api_deduction(from_date,to_date):
    url = "http://10.0.0.72:108/api/v1"
    
    # Các tham số truy vấn
    params = {
        'resource': 'api_BC_GiamTruDoanhThu',
        'method': 'select'
    }
    report_period = {"fromdate": from_date,
            "todate": to_date}
    # Nếu cần gửi tiêu đề (headers) cho yêu cầu, bạn có thể thêm vào đây
    headers = {
        'Content-Type': 'application/json'  # Định dạng JSON cho body
    }
    
    try:
        # Gửi yêu cầu POST
        response = requests.post(url, params=params, json=report_period, headers=headers)
        response.raise_for_status()  # Kiểm tra lỗi HTTP
        
        # Trả về dữ liệu JSON nếu yêu cầu thành công
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {e}")
        return None

def call_api_ar(from_date,to_date):
    url = "http://10.0.0.72:108/api/v1"
    
    # Các tham số truy vấn
    params = {
        'resource': 'api_DoiTuong_PhaiThu',
        'method': 'select'
    }
    report_period = {"fromdate": from_date,
            "todate": to_date}
    # Nếu cần gửi tiêu đề (headers) cho yêu cầu, bạn có thể thêm vào đây
    headers = {
        'Content-Type': 'application/json'  # Định dạng JSON cho body
    }
    
    try:
        # Gửi yêu cầu POST
        response = requests.post(url, params=params, json=report_period, headers=headers)
        response.raise_for_status()  # Kiểm tra lỗi HTTP
        
        # Trả về dữ liệu JSON nếu yêu cầu thành công
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {e}")
        return None

def call_api_detail_revenue(from_date,to_date,type):
    url = "http://10.0.0.72:108/api/v1"
    
    # Các tham số truy vấn
    params = {
        'resource': 'api_ChiTietDoanhThu',
        'method': 'select'
    }
    payload = {"fromdate": from_date,
            "todate": to_date,
            "hft_id2": type,
            }
    # Nếu cần gửi tiêu đề (headers) cho yêu cầu, bạn có thể thêm vào đây
    headers = {
        'Content-Type': 'application/json'  # Định dạng JSON cho body
    }
    
    try:
        # Gửi yêu cầu POST
        response = requests.post(url, params=params, json=payload, headers=headers)
        response.raise_for_status()  # Kiểm tra lỗi HTTP
        
        # Trả về dữ liệu JSON nếu yêu cầu thành công
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {e}")
        return None
    
def call_api_detail_deduction(from_date,to_date):
    url = "http://10.0.0.72:108/api/v1"
    
    # Các tham số truy vấn
    params = {
        'resource': 'api_ChiTietGiamTruDoanhThu',
        'method': 'select'
    }
    report_period = {"fromdate": from_date,
            "todate": to_date}
    # Nếu cần gửi tiêu đề (headers) cho yêu cầu, bạn có thể thêm vào đây
    headers = {
        'Content-Type': 'application/json'  # Định dạng JSON cho body
    }
    
    try:
        # Gửi yêu cầu POST
        response = requests.post(url, params=params, json=report_period, headers=headers)
        response.raise_for_status()  # Kiểm tra lỗi HTTP
        
        # Trả về dữ liệu JSON nếu yêu cầu thành công
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {e}")
        return None
    
def call_api_exam_revenue(from_date,to_date):
    url = "http://10.0.0.72:108/api/v1"
    
    # Các tham số truy vấn
    params = {
        'resource': 'api_DoanhThu_KSK',
        'method': 'select'
    }
    report_period = {"fromdate": from_date,
            "todate": to_date}
    # Nếu cần gửi tiêu đề (headers) cho yêu cầu, bạn có thể thêm vào đây
    headers = {
        'Content-Type': 'application/json'  # Định dạng JSON cho body
    }
    
    try:
        # Gửi yêu cầu POST
        response = requests.post(url, params=params, json=report_period, headers=headers)
        response.raise_for_status()  # Kiểm tra lỗi HTTP
        
        # Trả về dữ liệu JSON nếu yêu cầu thành công
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {e}")
        return None
    
def call_api_detail_exam_revenue(from_date,to_date):
    url = "http://10.0.0.72:108/api/v1"
    
    # Các tham số truy vấn
    params = {
        'resource': 'api_ChiTietDoanhThu_KSK',
        'method': 'select'
    }
    report_period = {"fromdate": from_date,
            "todate": to_date}
    # Nếu cần gửi tiêu đề (headers) cho yêu cầu, bạn có thể thêm vào đây
    headers = {
        'Content-Type': 'application/json'  # Định dạng JSON cho body
    }
    
    try:
        # Gửi yêu cầu POST
        response = requests.post(url, params=params, json=report_period, headers=headers)
        response.raise_for_status()  # Kiểm tra lỗi HTTP
        
        # Trả về dữ liệu JSON nếu yêu cầu thành công
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {e}")
        return None
    
def call_api_detail_inv_import(from_date,to_date,storage_ids):
    url = "http://10.0.0.72:108/api/v1"
    
    # Các tham số truy vấn
    params = {
        'resource': 'api_BC_ChiTietNhapKho',
        'method': 'select'
    }
    # Chuyển list thành chuỗi phân cách bằng dấu phẩy nếu là list
    if isinstance(storage_ids, list):
        storage_ids = ','.join(map(str, storage_ids))  # VD: [7,53] → '7,53'
    payload = {"from_date": from_date,
            "to_date": to_date,
            "storage_id": storage_ids,
            }
    # Nếu cần gửi tiêu đề (headers) cho yêu cầu, bạn có thể thêm vào đây
    headers = {
        'Content-Type': 'application/json'  # Định dạng JSON cho body
    }
    
    try:
        # Gửi yêu cầu POST
        response = requests.post(url, params=params, json=payload, headers=headers)
        response.raise_for_status()  # Kiểm tra lỗi HTTP
        
        # Trả về dữ liệu JSON nếu yêu cầu thành công
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {e}")
        return None
    
def call_api_detail_inv_export(from_date,to_date,storage_ids):
    url = "http://10.0.0.72:108/api/v1"
    
    # Các tham số truy vấn
    params = {
        'resource': 'api_BC_ChiTietXuatKho',
        'method': 'select'
    }
    if isinstance(storage_ids, list):
        storage_ids = ','.join(map(str, storage_ids))  # VD: [7,53] → '7,53'
    payload = {"from_date": from_date,
            "to_date": to_date,
            "storage_id": storage_ids,
            }
    # Nếu cần gửi tiêu đề (headers) cho yêu cầu, bạn có thể thêm vào đây
    headers = {
        'Content-Type': 'application/json'  # Định dạng JSON cho body
    }
    
    try:
        # Gửi yêu cầu POST
        response = requests.post(url, params=params, json=payload, headers=headers)
        response.raise_for_status()  # Kiểm tra lỗi HTTP
        
        # Trả về dữ liệu JSON nếu yêu cầu thành công
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {e}")
        return None
    
def call_api_detail_inv_export_PDT(from_date,to_date,storage_ids):
    url = "http://10.0.0.72:108/api/v1"
    
    # Các tham số truy vấn
    params = {
        'resource': 'api_BC_ChiTietXuatKhoPhieuDuTru',
        'method': 'select'
    }
    if isinstance(storage_ids, list):
        storage_ids = ','.join(map(str, storage_ids))  # VD: [7,53] → '7,53'
   
    payload = {"from_date": from_date,
            "to_date": to_date,
            "storage_id": storage_ids,
            }
    # Nếu cần gửi tiêu đề (headers) cho yêu cầu, bạn có thể thêm vào đây
    headers = {
        'Content-Type': 'application/json'  # Định dạng JSON cho body
    }
    
    try:
        # Gửi yêu cầu POST
        response = requests.post(url, params=params, json=payload, headers=headers)
        response.raise_for_status()  # Kiểm tra lỗi HTTP
        
        # Trả về dữ liệu JSON nếu yêu cầu thành công
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {e}")
        return None