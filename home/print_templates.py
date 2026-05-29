from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def template_A4landscape(pdf_canvas):
    pdf_canvas.setFont("Helvetica", 12)
    pdf_canvas.drawString(100, 750, "BỘ QUỐC PHÒNG")
    pdf_canvas.drawString(100, 735, "BỆNH VIỆN TWQĐ 108")
    # Bạn có thể thêm nhiều thành phần khác vào template tại đây
