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
#import matplotlib.pyplot as plt
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
from django.contrib.auth.models import Group
from django.db.models import Q
from django.utils.translation import gettext as _

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
            messages.error(request, _('اسم المستخدم أو كلمة المرور غير صحيحة.'))
    return render(request, 'myapp/login.html')

# عرض تسجيل الخروج
def logout_view(request):
    logout(request)
    messages.success(request, _('تم تسجيل الخروج بنجاح.'))
    return redirect('login')

# صفحة رئيسية تتطلب تسجيل الدخول
@login_required
def index(request):
    return render(request, 'myapp/index.html')



class ProductListView(ListView):
    model = Product
    template_name = 'myapp/product_list.html'
    context_object_name = 'products'

    def get_queryset(self):
        # جيب كل المجموعات اللي طارق أو أي مستخدم فيها
        user_groups = self.request.user.groups.all()
        # جيب المنتجات المرتبطة بأي من هاي المجموعات
        queryset = Product.objects.filter(team__in=user_groups)
        print(f"عدد المنتجات المرتبطة بمجموعات المستخدم {self.request.user.username}: {queryset.count()}")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        low_stock_products = self.get_queryset().filter(quantity__lt=F('min_stock'))
        context['low_stock_products'] = low_stock_products
        return context


# Add a new product
class ProductCreateView(CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'myapp/add_product.html'
    success_url = reverse_lazy('product_list')

    def form_valid(self, form):
        # اربط المنتج بالمستخدم الحالي
        form.instance.user = self.request.user
        # ======== إضافة لربط المنتج بفريق المستخدم ========
        form.instance.team = self.request.user.groups.first() # افترض إن المستخدم بينتمي لفريق واحد
        # لو المستخدم ممكن ينتمي لأكثر من فريق، ممكن تعدل دي حسب المنطق المطلوب
        # مثال لو عايز تربطه بكل الفرق:
        # form.instance.team.set(self.request.user.groups.all())
        # ======== نهاية الإضافة ========
        messages.success(self.request, _(f'تم إضافة المنتج {form.instance.product_name} بنجاح!'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("حدث خطأ في إضافة المنتج. يرجى التحقق من النموذج."))
        return super().form_invalid(form)

# سجل الحركات
@login_required
def movement_history(request):
    movements = Movement.objects.filter(product__user=request.user).order_by('-date')
    context = {
        'movements': movements,
    }
    return render(request, 'myapp/movement_history.html', context)

@login_required
def show_reports(request):
    movements = Movement.objects.filter(team__in=request.user.groups.all()).order_by('-date')
    context = {
        'movements': movements,
        'report_type': _('سجل الحركات'), # يمكنك تعديل هذا العنوان
    }
    return render(request, 'myapp/reports.html', context)

# قائمة المنتجات
@login_required
def product_list(request):
    # تم دمجه في ProductListView
    return redirect('product_list')

# حذف جميع المنتجات (تعديل للحذف فقط منتجات المستخدم)
@login_required
def clear_products(request):
    Product.objects.filter(user=request.user).delete()
    messages.success(request, _("تم حذف جميع المنتجات الخاصة بك بنجاح."))
    return redirect('product_list')

class ProductUpdateView(UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'myapp/edit_product.html'
    success_url = reverse_lazy('product_list')

    def get_queryset(self):
        return Product.objects.filter(team__in=self.request.user.groups.all())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.object  # مرر instance الفورم
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _(f'تم تعديل المنتج {form.instance.product_name} بنجاح!'), extra_tags=self.request.user.groups.first().name if self.request.user.groups.first() else 'all')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("حدث خطأ في تعديل المنتج. يرجى التحقق من النموذج."))
        return super().form_invalid(form)

# Delete a product (تعديل للتحقق من ملكية المنتج)
class ProductDeleteView(DeleteView):
    model = Product
    template_name = 'myapp/confirm_delete.html'
    success_url = reverse_lazy('product_list')

    def get_queryset(self):
        return Product.objects.filter(team__in=self.request.user.groups.all()) # فلترة حسب فريق المستخدم

    def delete(self, request, *args, **kwargs):
        messages.success(request, _("تم حذف المنتج بنجاح!"), extra_tags=request.user.groups.first().name if request.user.groups.first() else 'all')
        return super().delete(request, *args, **kwargs)

# إضافة كمية إلى منتج (تعديل لعرض فقط منتجات المستخدم والتحقق من ملكية المنتج)
@login_required
def add_quantity(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity_to_add = request.POST.get('quantity_to_add')
        try:
            quantity_to_add = float(quantity_to_add)
            if quantity_to_add <= 0:
                raise ValueError(_("الكمية يجب أن تكون أكبر من صفر"))

            # فلتر المنتجات حسب فريق المستخدم للتحقق من ملكية المنتج
            product = get_object_or_404(Product, pk=product_id, team__in=request.user.groups.all())
            # سجل الكمية الحالية قبل الإضافة
            quantity_before = product.quantity
            product.quantity += quantity_to_add
            product.save()
            # تسجيل حركة الاستلام بعد حفظ المنتج مع ربطها بفريق المنتج
            Movement.objects.create(
                product=product,
                movement_type='استلام',
                quantity=quantity_to_add,
                quantity_after=quantity_before,
                team=product.team  # ربط الحركة بفريق المنتج
            )
            messages.success(request, _(f'تمت إضافة {quantity_to_add} إلى {product.product_name} بنجاح!'), extra_tags=request.user.groups.first().name if request.user.groups.first() else 'all')
            return redirect('product_list')
        except ValueError as e:
            messages.error(request, _(f'خطأ: {str(e)}'))
            return redirect('product_list') # العودة لقائمة المنتجات مع عرض الخطأ

    # جلب المنتجات الخاصة بفريق المستخدم الحالي لعرضها في القائمة المنسدلة
    products_with_availability = []
    products = Product.objects.filter(team__in=request.user.groups.all())
    for product in products:
        products_with_availability.append({
            'id': product.id,
            'product_name': product.product_name,
            'product_code': product.product_code,
            'unit': product.unit,
            'available_quantity': product.quantity,
        })

    context = {
        'products': products_with_availability,
    }
    return render(request, 'myapp/add_quantity.html', context)

# تقرير الكميات المستلمة (Excel) (تعديل لعرض فقط حركات منتجات المستخدم)
@login_required
def received_report_excel(request):
    received_movements = Movement.objects.filter(
        movement_type='استلام',
        product__team__in=request.user.groups.all()
    )

    user_group_name = request.user.groups.first().name if request.user.groups.exists() else None

    team_name_list = []
    for movement in received_movements:
        if user_group_name == "فريق الصيانة":
            team_name_list.append(_("فريق الصيانة"))
        elif user_group_name == "فريق المواد الخام":
            team_name_list.append(_("فريق المواد الخام"))
        else:
            team_name_list.append(_("فريق غير محدد"))

    data = {
        _('اسم المنتج'): [movement.product.product_name for movement in received_movements],
        _('الكمية المدخلة'): [movement.quantity for movement in received_movements],
        _('التاريخ'): [movement.date.strftime('%Y-%m-%d') for movement in received_movements],
        _('الكمية المحدثة'): [movement.quantity_after for movement in received_movements],
        _('الوحدة'): [movement.product.unit for movement in received_movements],
        _('الفريق'): team_name_list,
    }

    df = pd.DataFrame(data)
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="received_report.xlsx"'
    df.to_excel(response, index=False)
    return response

# سحب كمية من منتج (تعديل لعرض فقط منتجات المستخدم والتحقق من ملكية المنتج)
@login_required
def withdraw_quantity(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity_to_withdraw = request.POST.get('quantity_to_withdraw')
        try:
            quantity_to_withdraw = float(quantity_to_withdraw)
            if quantity_to_withdraw <= 0:
                raise ValueError(_("الكمية يجب أن تكون أكبر من صفر"))

            # فلتر المنتجات حسب فريق المستخدم للتحقق من ملكية المنتج
            product = get_object_or_404(Product, pk=product_id, team__in=request.user.groups.all())
            if quantity_to_withdraw > product.quantity:
                raise ValueError(_("الكمية المسحوبة أكبر من المخزون المتوفر."))

            Movement.objects.create(
                product=product,
                movement_type='سحب',
                quantity=quantity_to_withdraw,
                quantity_after=product.quantity - quantity_to_withdraw,
                team=product.team  # اربط الحركة بفريق المنتج
            )
            product.quantity -= quantity_to_withdraw
            product.save()
            messages.success(request, _(f'تم سحب {quantity_to_withdraw} من {product.product_name} بنجاح!'), extra_tags=request.user.groups.first().name if request.user.groups.first() else 'all')
            return redirect('product_list')
        except ValueError as e:
            messages.error(request, _(f'خطأ: {str(e)}'))
            return redirect('product_list') # العودة لقائمة المنتجات مع عرض الخطأ

    # جلب المنتجات الخاصة بفريق المستخدم الحالي لعرضها في القائمة المنسدلة
    products_with_availability = []
    products = Product.objects.filter(team__in=request.user.groups.all())
    for product in products:
        products_with_availability.append({
            'id': product.id,
            'product_name': product.product_name,
            'product_code': product.product_code,
            'unit': product.unit,
            'available_quantity': product.quantity,
        })

    context = {
        'products': products_with_availability,
    }
    return render(request, 'myapp/withdraw_quantity.html', context)
@login_required
def withdrawn_report_excel(request):
    withdrawn_movements = Movement.objects.filter(
        movement_type='سحب',
        product__team__in=request.user.groups.all()
    )

    user_group_name = request.user.groups.first().name if request.user.groups.exists() else None

    team_name_list = []
    for movement in withdrawn_movements:
        if user_group_name == "فريق الصيانة":
            team_name_list.append(_("فريق الصيانة"))
        elif user_group_name == "فريق المواد الخام":
            team_name_list.append(_("فريق المواد الخام"))
        else:
            team_name_list.append(_("فريق غير محدد"))

    data = {
        _('اسم المنتج'): [movement.product.product_name for movement in withdrawn_movements],
        _('الكمية الصادرة'): [movement.quantity for movement in withdrawn_movements],
        _('التاريخ'): [movement.date.strftime('%Y-%m-%d') for movement in withdrawn_movements],
        _('الكمية الحالية'): [movement.quantity_after for movement in withdrawn_movements],
        _('الوحدة'): [movement.product.unit for movement in withdrawn_movements],
        _('الفريق'): team_name_list,
    }

    df = pd.DataFrame(data)
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="withdrawn_report.xlsx"'
    df.to_excel(response, index=False)
    return response

@login_required
def chart_view(request):
    withdrawn_data = Movement.objects.filter(
        movement_type='سحب',
        product__team__in=request.user.groups.all()  # فلترة حسب فريق المنتج
    ).values('product__product_name', 'product__unit').annotate(total_quantity=Sum('quantity')).order_by('-total_quantity')

    if not withdrawn_data.exists():
        return render(request, 'myapp/chart.html', {'error': _('لا توجد بيانات لعرض الرسم البياني.')})

    context = {
        'withdrawn_data': withdrawn_data,
    }
    return render(request, 'myapp/chart.html', context)
def get_products_by_name(request):
    if request.GET.get('name'):
        search_text = request.GET.get('name').strip()
        products = Product.objects.filter(
            product_name__icontains=search_text,
            team__in=request.user.groups.all()
        ).values('id', 'product_name', 'product_code', 'unit', 'quantity') # استخدمنا 'quantity'
        return JsonResponse(list(products), safe=False)
    else:
        products = Product.objects.filter(team__in=request.user.groups.all()).values('id', 'product_name', 'product_code', 'unit', 'quantity') # استخدمنا 'quantity' لود الصفحة اول مرة
        return JsonResponse(list(products), safe=False)
@login_required
def get_product_info(request, product_id):
    product = get_object_or_404(Product, id=product_id, user=request.user) # تحقق من ملكية المنتج
    data = {
        'product_name': product.product_name,
        'product_code': product.product_code,
        'quantity': product.quantity,
        'unit': product.unit,
        'min_stock': product.min_stock,
    }
    return JsonResponse(data)

def get_product_by_barcode(request):
    barcode = request.GET.get('barcode', None)
    if barcode:
        try:
            product = Product.objects.get(product_code=barcode)  # افترض إن عندك حقل اسمه 'product_code' للباركود
            data = {
                'id': product.id,
                'product_name': product.product_name,
                'unit': product.unit,
                'quantity': product.quantity,  # أو أي حقول تانية عايز ترجعها
                'product_code': product.product_code,
            }
            return JsonResponse(data)
        except Product.DoesNotExist:
            return JsonResponse({'error': 'لم يتم العثور على منتج بهذا الباركود'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'لم يتم إرسال رقم الباركود'}, status=400)
@login_required
def export_excel(request):
    products = Product.objects.filter(user=request.user)
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
    low_stock = Product.objects.filter(
        quantity__lt=F('min_stock'),
        team__in=request.user.groups.all()  # فلترة حسب فريق المستخدم
    )
    user = request.user
    groups = user.groups.all()
    group_names = [group.name for group in groups]
    context = {
        'low_stock_products': low_stock,
        'current_user': user,
        'current_user_groups': group_names,
    }
    return render(request, 'myapp/low_stock.html', context)

def forget_password(request):
    if request.method == 'POST':
        form = ForgetPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                token = default_token_generator.make_token(user)
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                reset_url = request.build_absolute_uri(
                    reverse_lazy('password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token})
                )
                # هنا المفروض تبعت إيميل برابط إعادة التعيين
                # في الواقع هتحتاج تستخدم Django's EmailBackend لإرسال الإيميلات
                print(f"رابط إعادة تعيين كلمة المرور: {reset_url}")
                messages.success(request, _('تم إرسال رابط إعادة تعيين كلمة المرور إلى بريدك الإلكتروني.'))
                return redirect('login')
            except User.DoesNotExist:
                messages.error(request, _('هذا البريد الإلكتروني غير مسجل.'))
    else:
        form = ForgetPasswordForm()
    return render(request, 'myapp/forget_password.html', {'form': form})

def password_reset_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            new_password1 = request.POST['new_password1']
            new_password2 = request.POST['new_password2']
            if new_password1 == new_password2:
                user.set_password(new_password1)
                user.save()
                messages.success(request, _('تم تعيين كلمة المرور الجديدة بنجاح. يمكنك تسجيل الدخول الآن.'))
                return redirect('login')
            else:
                messages.error(request, _('كلمتا المرور غير متطابقتين.'))
        else:
            return render(request, 'myapp/password_reset_confirm.html', {'form': {}})
    else:
        messages.error(request, _('رابط إعادة تعيين كلمة المرور غير صالح.'))
        return redirect('password_reset_done') # أو صفحة خطأ مناسبة
@login_required

@login_required
def inventory(request):

    # تم دمجه في ProductListView

    return redirect('product_list')


def password_reset_done(request):
    return render(request, 'myapp/password_reset_done.html')

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # يمكنك هنا تسجيل دخول المستخدم تلقائياً بعد التسجيل إذا أردت
            messages.success(request, _('تم إنشاء حسابك بنجاح. يمكنك تسجيل الدخول الآن.'))
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'myapp/register.html', {'form': form})

@login_required
def import_excel(request):
    if request.method == 'POST':
        excel_file = request.FILES['excel_file']
        df = pd.read_excel(excel_file)
        required_columns = ['product_name', 'product_code', 'quantity', 'unit', 'min_stock']
        if not all(col in df.columns for col in required_columns):
            messages.error(request, _('خطأ: ملف Excel لا يحتوي على جميع الأعمدة المطلوبة.'))
            return redirect('product_list')

        current_user_team = request.user.groups.first()
        if not current_user_team:
            messages.error(request, _('خطأ: المستخدم الحالي ليس لديه فريق محدد.'))
            return redirect('product_list')

        for index, row in df.iterrows():
            try:
                Product.objects.create(
                    user=request.user,
                    team=current_user_team,
                    product_name=row['product_name'],
                    product_code=row['product_code'],
                    quantity=row['quantity'],
                    unit=row['unit'],
                    min_stock=row['min_stock']
                )
            except Exception as e:
                messages.error(request, _(f'خطأ في استيراد الصف {index + 2}: {e}'))
                return redirect('product_list')

        messages.success(request, _('تم استيراد البيانات بنجاح.'))
        return redirect('product_list')
    return render(request, 'myapp/import_excel.html')

@login_required
def import_raw_materials(request):
    if request.method == 'POST':
        excel_file = request.FILES['excel_file']
        df = pd.read_excel(excel_file)
        required_columns = ['product_name', 'product_code', 'quantity', 'unit', 'min_stock']
        if not all(col in df.columns for col in required_columns):
            messages.error(request, _('خطأ: ملف Excel لا يحتوي على جميع الأعمدة المطلوبة.'))
            return redirect('product_list')

        raw_materials_team = Group.objects.filter(name='فريق المواد الخام').first()
        if not raw_materials_team:
            messages.error(request, _('خطأ: لم يتم العثور على فريق "فريق المواد الخام".'))
            return redirect('product_list')

        for index, row in df.iterrows():
            try:
                Product.objects.create(
                    user=request.user,
                    team=raw_materials_team,
                    product_name=row['product_name'],
                    product_code=row['product_code'],
                    quantity=row['quantity'],
                    unit=row['unit'],
                    min_stock=row['min_stock']
                )
            except Exception as e:
                messages.error(request, _(f'خطأ في استيراد الصف {index + 2}: {e}'))
                return redirect('product_list')

        messages.success(request, _('تم استيراد منتجات المواد الخام بنجاح.'))
        return redirect('product_list')
    return render(request, 'myapp/import_excel.html', {'import_type': 'raw_materials'})

@login_required
def import_maintenance(request):
    if request.method == 'POST':
        excel_file = request.FILES['excel_file']
        df = pd.read_excel(excel_file)
        required_columns = ['product_name', 'product_code', 'quantity', 'unit', 'min_stock']
        if not all(col in df.columns for col in required_columns):
            messages.error(request, _('خطأ: ملف Excel لا يحتوي على جميع الأعمدة المطلوبة.'))
            return redirect('product_list')

        maintenance_team = Group.objects.filter(name='فريق الصيانة').first()
        if not maintenance_team:
            messages.error(request, _('خطأ: لم يتم العثور على فريق "فريق الصيانة".'))
            return redirect('product_list')

        for index, row in df.iterrows():
            try:
                Product.objects.create(
                    user=request.user,
                    team=maintenance_team,
                    product_name=row['product_name'],
                    product_code=row['product_code'],
                    quantity=row['quantity'],
                    unit=row['unit'],
                    min_stock=row['min_stock']
                )
            except Exception as e:
                messages.error(request, _(f'خطأ في استيراد الصف {index + 2}: {e}'))
                return redirect('product_list')

        messages.success(request, _('تم استيراد منتجات الصيانة بنجاح.'))
        return redirect('product_list')
    return render(request, 'myapp/import_excel.html', {'import_type': 'maintenance'})
