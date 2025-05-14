import os
import django
from barcode import Code128
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import openpyxl
from arabic_reshaper import reshape
from bidi.algorithm import get_display

# تهيئة بيئة Django (اسم مشروعك هو myproject)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Product # استورد موديل Product من تطبيقك myapp

def generate_barcode_with_text(product_code, product_name, filename="barcode"):
    """يولد باركود Code 128 ويحفظه كملف PNG مع اسم المنتج تحته (يدعم النصوص ثنائية الاتجاه)."""
    try:
        # توليد الباركود باستخدام رمز المنتج فقط
        barcode = Code128(product_code, writer=ImageWriter())
        buffer = BytesIO()
        barcode.write(buffer)
        barcode_image = Image.open(buffer)

        # تحديد أبعاد الصورة الجديدة
        barcode_width, barcode_height = barcode_image.size
        text_height_code = 20
        text_height_name = 20
        spacing = 5
        new_height = barcode_height + text_height_code + text_height_name + 2 * spacing
        new_image = Image.new('RGB', (barcode_width, new_height), 'white')
        draw = ImageDraw.Draw(new_image)

        # لصق الباركود
        new_image.paste(barcode_image, (0, 0))

        # اختيار الخط (تأكد من وجود خط يدعم العربية/العبرية)
        try:
            font_code = ImageFont.truetype("arial.ttf", 14)
            font_name = ImageFont.truetype("arial.ttf", 16)
        except IOError:
            font_code = ImageFont.load_default()
            font_name = ImageFont.load_default()

        # كتابة كود المنتج
        text_code_width = draw.textlength(product_code, font=font_code)
        text_code_x = (barcode_width - text_code_width) // 2
        text_code_y = barcode_height + spacing
        draw.text((text_code_x, text_code_y), product_code, fill='black', font=font_code)

        # معالجة اسم المنتج باستخدام arabic_reshaper و bidi
        reshaped_text = reshape(product_name)
        bidi_text = get_display(reshaped_text)

        # كتابة اسم المنتج المعالج
        text_name_width = draw.textlength(bidi_text, font=font_name)
        text_name_x = (barcode_width - text_name_width) // 2
        text_name_y = text_code_y + text_height_code + spacing
        filename_with_name = f"{filename}_{product_code}"
        draw.text((text_name_x, text_name_y), bidi_text, fill='black', font=font_name)

        new_image.save(f"{filename_with_name}.png")
        print(f"تم توليد الباركود لـ {product_name} ({product_code}) وحفظه باسم {filename_with_name}.png")

    except Exception as e:
        print(f"حدث خطأ أثناء توليد الباركود لـ {product_name} ({product_code}): {e}")

def generate_bulk_barcodes(excel_filepath):
    """يقرأ رموز المنتجات وأسمائها من ملف XLSX لتوليد الباركودات مع أسمائها."""
    try:
        workbook = openpyxl.load_workbook(excel_filepath)
        sheet = workbook.active  # أو حدد اسم الشيت لو مش الأول

        # تخطي أول سطر لو فيه عناوين
        header_skipped = False

        for row in sheet.iter_rows():
            if not header_skipped:
                header_skipped = True
                continue

            if len(row) >= 2:
                product_code_cell = row[0]
                product_name_cell = row[1]

                if product_code_cell.value is not None and product_name_cell.value is not None:
                    product_code = str(product_code_cell.value)
                    product_name = str(product_name_cell.value)
                    generate_barcode_with_text(product_code, product_name)
    except FileNotFoundError:
        print(f"Error: File not found at {excel_filepath}")
    except Exception as e:
        print(f"An error occurred: {e}")

# مثال لاستخدام الدالة مع ملف XLSX فيه رموز المنتجات في العمود الأول واسم المنتج في العمود الثاني
generate_bulk_barcodes("products_codes.xlsx")
