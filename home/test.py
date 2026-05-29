import requests
from collections import defaultdict
from datetime import datetime
import pandas as pd

    
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
   
from_date = "2025-07-01"
to_date = "2025-07-04"
storage_ids = [7,53]
response = call_api_detail_inv_import(from_date,to_date,storage_ids)


detail_inv_import_series = response.get('data', [])
df_detail_inv_import = pd.DataFrame(detail_inv_import_series)
#report_period = {"fromdate": "2024-09-24",
#        "todate": "2024-09-24"}
print (response)
