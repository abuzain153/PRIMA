
from barcode import Code128
from barcode.writer import ImageWriter
import csv

def generate_barcode(product_code, filename="barcode"):
    """يولد باركود Code 128 ويحفظه كملف PNG."""
    barcode = Code128(product_code, writer=ImageWriter())
    filename = f"{filename}_{product_code}"  # إضافة رمز المنتج لاسم الملف
    barcode.save(filename)
    print(f"تم توليد الباركود لـ {product_code} وحفظه باسم {filename}.png")

def generate_bulk_barcodes(csv_filepath):
    """يقرأ رموز المنتجات من ملف CSV ويولد باركودات ليها."""
    with open(csv_filepath, 'r') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # تخطي السطر الأول لو فيه عناوين
        for row in reader:
            product_code = row[0]  # افترض إن رمز المنتج في العمود الأول
            generate_barcode(product_code)

# مثال لاستخدام الدالة مع رمز المنتج بتاعك
# product_code = "RM010203"
# generate_barcode(product_code)

# لو عندك ملف اسمه products.csv فيه رموز المنتجات في العمود الأول، شغل الدالة دي
generate_bulk_barcodes("products.csv")
