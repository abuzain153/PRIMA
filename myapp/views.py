from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, F
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Product, Movement
from .forms import ProductForm, ForgetPasswordForm, RegistrationForm
import pandas as pd
from io import BytesIO
import matplotlib.pyplot as plt
import base64
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.contrib.auth.models import User
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings # عشان نوصل لإعدادات البريد الإلكتروني
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
# عرض تسجيل الدخول
def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('index')
        else:
            messages.error(request, 'اسم المستخدم أو كلمة المرور غير صحيحة.')
    return render(request, 'myapp/login.html')

# عرض تسجيل الخروج
def logout_view(request):
    logout(request)
    messages.success(request, 'تم تسجيل الخروج بنجاح.')
    return redirect('login')

# صفحة رئيسية تتطلب تسجيل الدخول
@login_required
def index(request):
    return render(request, 'myapp/index.html')

# List products (تعديل لعرض تنبيهات المخزون المنخفض)
class ProductListView(ListView):
    model = Product
    template_name = 'myapp/product_list.html'
    context_object_name = 'products'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        low_stock_threshold = 10  # يمكنك تعديل هذا الرقم
        low_stock_products = Product.objects.filter(quantity__lt=F('min_stock'))
        context['low_stock_products'] = low_stock_products
        return context

# Add a new product
class ProductCreateView(CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'myapp/add_product.html'
    success_url = reverse_lazy('product_list')

    def form_valid(self, form):
        messages.success(self.request, f'تم إضافة المنتج {form.instance.product_name} بنجاح!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "حدث خطأ في إضافة المنتج. يرجى التحقق من النموذج.")
        return super().form_invalid(form)

# سجل الحركات
@login_required
def movement_history(request):
    movements = Movement.objects.all().order_by('-date')
    context = {
        'movements': movements,
    }
    return render(request, 'myapp/movement_history.html', context)

# عرض التقارير
@login_required
def show_reports(request):
    movements = Movement.objects.all().order_by('-date')
    context = {
        'movements': movements,
        'report_type': 'سجل الحركات', # يمكنك تعديل هذا العنوان
    }
    return render(request, 'myapp/reports.html', context)

# قائمة المنتجات
@login_required
def product_list(request):
    # تم دمجه في ProductListView
    return redirect('product_list')

# حذف جميع المنتجات
@login_required
def clear_products(request):
    Product.objects.all().delete()
    messages.success(request, "تم حذف جميع المنتجات بنجاح.")
    return redirect('product_list')

# Edit an existing product
class ProductUpdateView(UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'myapp/edit_product.html'
    success_url = reverse_lazy('product_list')

    def form_valid(self, form):
        messages.success(self.request, f'تم تعديل المنتج {form.instance.product_name} بنجاح!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "حدث خطأ في تعديل المنتج. يرجى التحقق من النموذج.")
        return super().form_invalid(form)

# Delete a product
class ProductDeleteView(DeleteView):
    model = Product
    template_name = 'myapp/confirm_delete.html'
    success_url = reverse_lazy('product_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, "تم حذف المنتج بنجاح.")
        return super().delete(request, *args, **kwargs)

# إضافة كمية إلى منتج
@login_required
def add_quantity(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity_to_add = request.POST.get('quantity_to_add')
        try:
            quantity_to_add = float(quantity_to_add)
            if quantity_to_add <= 0:
                raise ValueError("الكمية يجب أن تكون أكبر من صفر")

            product = get_object_or_404(Product, pk=product_id)
            # هنا بيتم تحديث الكمية في جدول Product مباشرةً
            product.quantity += quantity_to_add
            product.save()
            messages.success(request, f'تمت إضافة {quantity_to_add} إلى {product.product_name} بنجاح!')
            return redirect('product_list')
        except ValueError as e:
            messages.error(request, f'خطأ: {str(e)}')
            return redirect('product_list') # العودة لقائمة المنتجات مع عرض الخطأ

    products_with_availability = []
    products = Product.objects.all()
    for product in products:
        products_with_availability.append({
            'id': product.id,
            'product_name': product.product_name,
            'product_code': product.product_code,
            'unit': product.unit,
            'available_quantity': product.quantity,  # استخدام الكمية من جدول Product
        })

    context = {
        'products': products_with_availability,
    }
    return render(request, 'myapp/add_quantity.html', context)

# تقرير الكميات المستلمة (Excel)
@login_required
def received_report_excel(request):
    received_movements = Movement.objects.filter(movement_type='استلام')
    data = {
        'اسم المنتج': [movement.product.product_name for movement in received_movements],
        'الكمية المستلمة': [movement.quantity for movement in received_movements],
        'التاريخ': [movement.date.strftime('%Y-%m-%d') for movement in received_movements],
        'الكمية بعد التعديل': [movement.quantity_after for movement in received_movements],
        'الوحدة': [movement.product.unit for movement in received_movements],
    }
    df = pd.DataFrame(data)
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="received_report.xlsx"'
    df.to_excel(response, index=False)
    return response

# سحب كمية من منتج
@login_required
def withdraw_quantity(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity_to_withdraw = request.POST.get('quantity_to_withdraw')
        try:
            quantity_to_withdraw = float(quantity_to_withdraw)
            if quantity_to_withdraw <= 0:
                raise ValueError("الكمية يجب أن تكون أكبر من صفر")

            product = get_object_or_404(Product, pk=product_id)
            if quantity_to_withdraw > product.quantity:
                raise ValueError("الكمية المسحوبة أكبر من المخزون المتوفر.")

            Movement.objects.create(
                product=product,
                movement_type='سحب',
                quantity=quantity_to_withdraw,
                quantity_after=product.quantity - quantity_to_withdraw # تسجيل الكمية بعد السحب
            )
            product.quantity -= quantity_to_withdraw
            product.save()
            messages.success(request, f'تم سحب {quantity_to_withdraw} من {product.product_name} بنجاح!')
            return redirect('product_list')
        except ValueError as e:
            messages.error(request, f'خطأ: {str(e)}')
            return redirect('product_list') # العودة لقائمة المنتجات مع عرض الخطأ

    products_with_availability = []
    products = Product.objects.all()
    for product in products:
        products_with_availability.append({
            'id': product.id,
            'product_name': product.product_name,
            'product_code': product.product_code,
            'unit': product.unit,
            'available_quantity': product.quantity,  # استخدام الكمية من جدول Product
        })

    context = {
        'products': products_with_availability,
    }
    return render(request, 'myapp/withdraw_quantity.html', context)

# تقرير الكميات المسحوبة (Excel)
@login_required
def withdrawn_report_excel(request):
    withdrawn_movements = Movement.objects.filter(movement_type='سحب')
    data = {
        'اسم المنتج': [movement.product.product_name for movement in withdrawn_movements],
        'الكمية المسحوبة': [movement.quantity for movement in withdrawn_movements],
        'التاريخ': [movement.date.strftime('%Y-%m-%d') for movement in withdrawn_movements],
        'الكمية بعد التعديل': [movement.quantity_after for movement in withdrawn_movements],
        'الوحدة': [movement.product.unit for movement in withdrawn_movements],
    }
    df = pd.DataFrame(data)
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="withdrawn_report.xlsx"'
    df.to_excel(response, index=False)
    return response

@login_required
def chart_view(request):
    withdrawn_data = Movement.objects.filter(movement_type='سحب').values('product__product_name', 'product__unit').annotate(total_quantity=Sum('quantity')).order_by('-total_quantity')

    if not withdrawn_data.exists():
        return render(request, 'myapp/chart.html', {'error': 'لا توجد بيانات لعرض الرسم البياني.'})

    context = {
        'withdrawn_data': withdrawn_data,
    }
    return render(request, 'myapp/chart.html', context)




@login_required
def get_product_info(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    data = {
        'product_name': product.product_name,
        'product_code': product.product_code,
        'quantity': product.quantity,
        'unit': product.unit,
        'min_stock': product.min_stock,
    }
    return JsonResponse(data)

@login_required
def export_excel(request):
    products = Product.objects.all()
    data = {
        'اسم المنتج': [product.product_name for product in products],
        'رمز المنتج': [product.product_code for product in products],
        'الكمية': [product.quantity for product in products],
        'الوحدة': [product.unit for product in products],
        'الحد الأدنى': [product.min_stock for product in products],
    }
    df = pd.DataFrame(data)
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="inventory.xlsx"'
    df.to_excel(response, index=False)
    return response

@login_required
def low_stock_products(request):
    """
    عرض قائمة بالمنتجات التي يقل مخزونها عن الحد الأدنى.
    """
    low_stock = Product.objects.filter(quantity__lt=F('min_stock'))
    context = {
        'low_stock': low_stock,
    }
    return render(request, 'myapp/low_stock.html', context)
def forget_password(request):
    if request.method == 'POST':
        form = ForgetPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                subject = 'إعادة تعيين كلمة المرور - برنامج إدارة المخازن'
                context = {
                    'email': user.email,
                    'domain': request.META['HTTP_HOST'],
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': default_token_generator.make_token(user),
                }
                form.send_mail(
                    'emails/password_reset_subject.txt',
                    'emails/password_reset_body.txt',
                    context,
                    settings.DEFAULT_FROM_EMAIL
                )
                messages.success(request, 'تم إرسال رابط إعادة تعيين كلمة المرور إلى بريدك الإلكتروني.')
                return redirect('login')
            except User.DoesNotExist:
                messages.error(request, 'هذا البريد الإلكتروني غير مسجل.')
    else:
        form = ForgetPasswordForm()
    return render(request, 'forget_password.html', {'form': form})

def password_reset_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            if new_password and new_password == confirm_password:
                user.set_password(new_password)
                user.save()
                messages.success(request, 'تم تعيين كلمة المرور الجديدة بنجاح. يمكنك تسجيل الدخول الآن.')
                return redirect('login')
            else:
                messages.error(request, 'كلمتا المرور غير متطابقتين.')
        else:
            return render(request, 'password_reset_confirm.html', {'form': {}, 'uidb64': uidb64, 'token': token})
    else:
        messages.error(request, 'رابط إعادة تعيين كلمة المرور غير صالح.')
        return redirect('login')

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'تم إنشاء حسابك بنجاح. يمكنك تسجيل الدخول الآن.')
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # هنا ممكن تعمل تفعيل للحساب عن طريق الإيميل لو عايز
            messages.success(request, 'تم إنشاء حسابك بنجاح. يمكنك تسجيل الدخول الآن.')
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})
@login_required
def inventory(request):
    # تم دمجه في ProductListView
    return redirect('product_list')

@login_required
def import_excel(request):
    if request.method == 'POST':
        excel_file = request.FILES['excel_file']
        try:
            df = pd.read_excel(excel_file)
            required_columns = ['product_name', 'product_code', 'quantity', 'unit', 'min_stock']
            if not all(col in df.columns for col in required_columns):
                messages.error(request, 'خطأ: ملف Excel لا يحتوي على جميع الأعمدة المطلوبة.')
                return redirect('import_excel')
            products = []
            for _, row in df.iterrows():
                if all(pd.notnull(row)):
                    products.append(Product(
                        product_name=row['product_name'].strip(),
                        product_code=row['product_code'].strip(),
                        quantity=float(row['quantity']),
                        unit=row['unit'].strip(),
                        min_stock=float(row['min_stock'])
                    ))
            Product.objects.bulk_create(products)
            messages.success(request, 'تم استيراد البيانات بنجاح.')
            return redirect('product_list')
        except Exception as e:
            messages.error(request, f'خطأ: حدث خطأ أثناء قراءة ملف Excel: {e}')
            return redirect('import_excel')
    return render(request, 'myapp/import_excel.html')
