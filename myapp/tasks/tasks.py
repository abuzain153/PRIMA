from celery import shared_task
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from io import BytesIO
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from django.contrib.auth.models import User
from myapp.models import Product # مهم جداً تستورد الـ Model من تطبيقك
from django.db.models import F

@shared_task
def generate_low_stock_report(recipient_emails, report_format):
    low_stock_data = Product.objects.filter(
        quantity__lt=F('min_stock')
    ).values('product_name', 'product_code', 'quantity', 'unit', 'min_stock')

    if not low_stock_data:
        return "لا توجد منتجات ناقصة لإرسال تقرير بها."

    if report_format == 'excel':
        df = pd.DataFrame(list(low_stock_data))
        buffer = BytesIO()
        df.to_excel(buffer, index=False, sheet_name='نواقص المخزون')
        file_data = buffer.getvalue()
        file_name = 'تقرير_نواقص_المخزون_مجدول.xlsx'
        file_mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    elif report_format == 'pdf':
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        textobject = p.beginText(inch, letter[1] - inch)
        for item in low_stock_data:
            textobject.textLine(f"{item['product_name']} ({item['product_code']}): {item['quantity']} {item['unit']} (Min: {item['min_stock']})")
        p.drawText(textobject)
        p.showPage()
        p.save()
        file_data = buffer.getvalue()
        file_name = 'تقرير_نواقص_المخزون_مجدول.pdf'
        file_mime_type = 'application/pdf'
    else:
        return "صيغة تقرير غير مدعومة."

    return file_name, file_data, file_mime_type

@shared_task
def send_scheduled_low_stock_report(recipient_emails, report_format, message):
    file_name, file_data, file_mime_type = generate_low_stock_report(recipient_emails, report_format)

    email = EmailMessage(
        'تقرير نواقص المخزون',
        message,
        'abuzain186@gmail.com', # بدل بإيميل المرسل بتاعك
        recipient_emails
    )
    email.attach(file_name, file_data, file_mime_type)
    email.send()
    return f"تم إرسال التقرير إلى: {', '.join(recipient_emails)}"
