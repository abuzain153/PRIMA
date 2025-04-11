from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Movement
from django.db.models import Sum
from django.db import models
from django.http import HttpResponse, JsonResponse
import pandas as pd
from io import BytesIO
import openpyxl
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
import matplotlib.pyplot as plt
import base64
from .forms import ProductForm

# عرض قائمة المنتجات
def product_list(request):
    products = Product.objects.all()
    return render(request, 'myapp/product_list.html', {'products': products})

# إضافة منتج جديد
def add_product(request):
    if request.method == 'POST':
        product_name = request.POST.get('product_name')
        product_code = request.POST.get('product_code')
        quantity = request.POST.get('quantity')
        unit = request.POST.get('unit')
        min_stock = request.POST.get('min_stock')

        try:
            quantity = float(quantity)
            min_stock = float(min_stock)

            if quantity <= 0 or min_stock <= 0:
                raise ValueError("الكمية والحد الأدنى يجب أن تكون أكبر من صفر")

            # إنشاء المنتج
            Product.objects.create(
                product_name=product_name,
                product_code=product_code,
                quantity=quantity,
                unit=unit,
                min_stock=min_stock
            )

            messages.success(request, f'تم إضافة المنتج {product_name} بنجاح!')
            return redirect('product_list')

        except ValueError as e:
            messages.error(request, f'خطأ: {str(e)}')
            return render(request, 'myapp/add_product.html')

    return render(request, 'myapp/add_product.html')

# تعديل منتج (باستخدام Django Forms)
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تعديل المنتج بنجاح.")
            return redirect('product_list')
        else:
            messages.error(request, "حدث خطأ في تعديل المنتج. يرجى التحقق من النموذج.")
    else:
        form = ProductForm(instance=product)
    return render(request, 'edit_product.html', {'form': form, 'product': product})

# حذف منتج
def delete_product(request, product_id):
    product = Product.objects.get(id=product_id)
    product.delete()
    return redirect('product_list')

# عرض الرسم البياني
def show_graph(request):
    # جلب البيانات الخاصة بالمسحوبات
    movements = Movement.objects.filter(movement_type='سحب')
    
    # التأكد إذا كانت البيانات فارغة
    if not movements:
        # إرجاع استجابة توضح أنه لا توجد بيانات
        return render(request, 'graph.html', {'error': 'لا يوجد مسحوبات'})
    
    # استخراج التواريخ والكميات
    dates = [movement.date.strftime('%Y-%m-%d') for movement in movements]
    quantities = [movement.quantity for movement in movements]
    
    # إنشاء الرسم البياني باستخدام matplotlib
    fig, ax = plt.subplots()
    ax.plot(dates, quantities, marker='o')
    ax.set(xlabel='التاريخ', ylabel='الكمية المسحوبة', title='الكميات المسحوبة عبر الأيام')
    ax.grid()
    
    # حفظ الرسم البياني في الذاكرة
    buf = BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    
    # ترميز الصورة إلى base64
    image_data = base64.b64encode(buf.getvalue()).decode('utf-8')
    
    # إرجاع الصورة ضمن الاستجابة
    return render(request, 'graph.html', {'graph': image_data})
def chart_view(request):
    withdrawn_data = Movement.objects.filter(movement_type='سحب').values('product__product_name').annotate(total_quantity=Sum('quantity'))
    
    # التأكد من أن البيانات موجودة
    if not withdrawn_data:
        return render(request, 'chart.html', {'error': 'لا توجد بيانات للمسحوبات'})
    
    return render(request, 'chart.html', {'withdrawn_data': withdrawn_data})   
    # عرض الصورة في القالب
    return render(request, 'graph.html', {'graph': image_data})

def add_quantity(request):
    print("=== تم تنفيذ POST للإضافة ===")
    print(f"ID المنتج: {request.POST.get('product_id')}")
    print(f"الكمية المطلوب إضافتها: {request.POST.get('quantity_to_add')}")

    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity_to_add = request.POST.get('quantity_to_add')

        try:
            quantity_to_add = float(quantity_to_add)
            if quantity_to_add <= 0:
                raise ValueError("الكمية يجب أن تكون أكبر من صفر")
        except ValueError as e:
            return render(request, 'myapp/add_quantity.html', {'error': f'الكمية يجب أن تكون رقمًا صحيحًا: {str(e)}', 'products': Product.objects.all()})

        product = get_object_or_404(Product, pk=product_id)
        product.quantity += quantity_to_add
        product.save()

        current_date = timezone.now()

        Movement.objects.create(
            product=product,
            movement_type='استلام',
            quantity=quantity_to_add,
            date=current_date
        )
        messages.success(request, f'تمت إضافة {quantity_to_add} إلى {product.product_name} بنجاح!')
        return redirect('product_list')

    return render(request, 'myapp/add_quantity.html', {'products': Product.objects.all()})

# سحب كمية من منتج
def withdraw_quantity(request):
    print("=== تم تنفيذ POST للسحب ===")
    print(f"ID المنتج: {request.POST.get('product_id')}")
    print(f"الكمية المطلوبة للسحب: {request.POST.get('quantity_to_withdraw')}")

    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity_to_withdraw = request.POST.get('quantity_to_withdraw')

        # تحقق من وجود product_id
        if not product_id:
            return render(request, 'myapp/withdraw_quantity.html', {'error': 'المنتج غير محدد', 'products': Product.objects.all()})

        try:
            # تحويل الكمية إلى عدد عشري
            quantity_to_withdraw = float(quantity_to_withdraw)
            if quantity_to_withdraw <= 0:
                raise ValueError("الكمية يجب أن تكون أكبر من صفر")
        except ValueError as e:
            return render(request, 'myapp/withdraw_quantity.html', {'error': f'الكمية يجب أن تكون رقمًا صحيحًا: {str(e)}', 'products': Product.objects.all()})

        # استرجاع المنتج باستخدام id
        product = get_object_or_404(Product, pk=product_id)

        # التحقق من وجود الكمية المطلوبة
        if product.quantity >= quantity_to_withdraw:
            # تقليل الكمية المتاحة من المخزون
            product.quantity -= quantity_to_withdraw
            product.save()

            current_date = timezone.now()

            # تسجيل حركة السحب
            Movement.objects.create(
                product=product,
                movement_type='سحب',
                quantity=quantity_to_withdraw,
                date=current_date
            )

            # إعادة التوجيه إلى صفحة قائمة المنتجات
            return redirect(reverse('product_list'))
        else:
            # إذا كانت الكمية غير كافية
            return render(request, 'myapp/withdraw_quantity.html', {'error': 'لا توجد كمية كافية', 'products': Product.objects.all()})

    # إذا كانت الطريقة غير POST، يتم عرض الصفحة
    return render(request, 'myapp/withdraw_quantity.html', {'products': Product.objects.all()})

# عرض التقارير
def show_reports(request):
    return render(request, 'myapp/show_reports.html')

# دالة مساعدة لإنشاء تقارير Excel
def create_excel_report(queryset, movement_type):
    data = {'اسم المنتج': [], 'الكمية': [], 'التاريخ': []}
    for movement in queryset:
        # تحويل التاريخ إلى تاريخ غير واعي بالمنطقة الزمنية
        date_unaware = movement.date.replace(tzinfo=None)
        data['اسم المنتج'].append(movement.product.product_name)
        data['الكمية'].append(movement.quantity)
        data['التاريخ'].append(date_unaware)  # استخدام التاريخ غير الواعي بالمنطقة الزمنية
    df = pd.DataFrame(data)
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="{movement_type}_report.xlsx"'
    df.to_excel(response, index=False)
    return response

# تقرير الكميات المستلمة
def received_report_excel(request):
    movements = Movement.objects.filter(movement_type='استلام')
    return create_excel_report(movements, 'received')

# تقرير الكميات المسحوبة
def withdrawn_report_excel(request):
    movements = Movement.objects.filter(movement_type='سحب')
    return create_excel_report(movements, 'withdrawn')

# الحصول على تفاصيل المنتج
def get_product_info(request, product_id):
    try:
        product = get_object_or_404(Product, id=product_id)
        data = {
            'product_code': product.product_code,
            'product_name': product.product_name,
            'quantity': product.quantity,
            'unit': product.unit,
            'min_stock': product.min_stock
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# عرض المنتجات التي بها مخزون منخفض
def low_stock_products(request):
    low_stock = Product.objects.filter(quantity__lt=models.F('min_stock'))
    for product in low_stock:
        print(f"Product Name: {product.product_name}, Product Code: {product.product_code}")
    return render(request, 'myapp/low_stock.html', {'low_stock': low_stock})

# استيراد بيانات من Excel
def import_excel(request):
    if request.method == 'POST':
        excel_file = request.FILES['excel_file']
        try:
            df = pd.read_excel(excel_file)
            columns = df.columns.tolist()

            required_columns = ['product_name', 'product_code', 'quantity', 'unit', 'min_stock']
            if not all(col in columns for col in required_columns):
                messages.error(request, 'خطأ: ملف Excel لا يحتوي على جميع الأعمدة المطلوبة.')
                return redirect('import_excel')

            for _, row in df.iterrows():
                if all(pd.notnull(row)):
                    try:
                        product_name = row['product_name'].strip()
                        product_code = row['product_code'].strip()
                        quantity = float(row['quantity'])
                        unit = row['unit'].strip()
                        min_stock = float(row['min_stock'])

                        if not product_name or not product_code or quantity is None or not unit or min_stock is None:
                            messages.error(request, 'خطأ: توجد قيم فارغة في ملف Excel.')
                            return redirect('import_excel')

                        Product.objects.update_or_create(
                            product_code=product_code,
                            defaults={
                                'product_name': product_name,
                                'quantity': quantity,
                                'unit': unit,
                                'min_stock': min_stock,
                            }
                        )
                    except ValueError as e:
                        messages.error(request, f'خطأ: قيمة غير صحيحة في ملف Excel: {e}')
                        return redirect('import_excel')

            messages.success(request, 'تم استيراد البيانات بنجاح.')
            return redirect('product_list')

        except Exception as e:
            messages.error(request, f'خطأ: حدث خطأ أثناء قراءة ملف Excel: {e}')
            return redirect('import_excel')

    return render(request, 'myapp/import_excel.html')
# تصدير بيانات إلى Excel
def export_excel(request):
    products = Product.objects.all()
    data = {'اسم المنتج': [], 'رمز المنتج': [], 'الكمية': [], 'الوحدة': [], 'الحد الأدنى': []}
    for product in products:
        data['اسم المنتج'].append(product.product_name)
        data['رمز المنتج'].append(product.product_code)
        data['الكمية'].append(product.quantity)
        data['الوحدة'].append(product.unit)
        data['الحد الأدنى'].append(product.min_stock)

    df = pd.DataFrame(data)
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="inventory.xlsx"'
    df.to_excel(response, index=False)
    return response

def clear_products(request):
    Product.objects.all().delete()
    messages.success(request, 'تم مسح جميع المنتجات بنجاح.')
    return redirect('import_excel')