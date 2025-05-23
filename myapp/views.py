from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, F
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Product, Movement , Warehouse , ProductWarehouse
from .forms import ProductForm, ForgetPasswordForm, RegistrationForm ,WarehouseSelectionForm
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
from .models import Notification  # تأكد إن عندك موديل Notification
from django.contrib.auth.mixins import LoginRequiredMixin
from decimal import Decimal, InvalidOperation
from django.db import models
from .forms import WithdrawQuantityFromWarehousesForm
from .forms import AddQuantityToWarehousesForm
import io, xlsxwriter
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import datetime
@login_required
def notifications_list(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'myapp/notifications.html', {'notifications': notifications})

@login_required
def mark_as_read(request, notification_id):
    try:
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        notification.delete() # تم إضافة سطر الحذف هنا
        # إرجاع المستخدم للصفحة اللي كان فيها
        return redirect(request.META.get('HTTP_REFERER', 'index'))
    except Notification.DoesNotExist:
        messages.error(request, _('الإشعار غير موجود.'))
        return redirect('index') # أو أي صفحة مناسبة في حالة عدم وجود الإشعار
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



class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'myapp/product_list.html'
    context_object_name = 'products'
    ordering = ['-id'] # ترتيب المنتجات تنازلياً حسب الـ ID (الأحدث أولاً)

    def get_queryset(self):
        # جلب المجموعات التي ينتمي إليها المستخدم الحالي
        user_groups = self.request.user.groups.all()

        # فلترة المنتجات بناءً على المجموعات التي ينتمي إليها المستخدم
        # (يفترض وجود حقل 'team' في موديل Product يرتبط بـ Group)
        queryset = Product.objects.filter(team__in=user_groups)

        # تطبيق منطق البحث المدمج
        search_term = self.request.GET.get('search')
        if search_term:
            queryset = queryset.filter(
                models.Q(product_name__icontains=search_term) |
                models.Q(product_code__icontains=search_term)
            )

        # تطبيق الترتيب المحدد
        queryset = queryset.order_by(*self.ordering)

        return queryset

    def get_context_data(self, **kwargs):
        # استدعاء الدالة الأصلية للحصول على الـ context الأساسي
        context = super().get_context_data(**kwargs)

        # فلترة المنتجات قليلة المخزون من الـ queryset الذي تم جلبه
        # (يفترض وجود حقل 'min_stock' في موديل Product)
        low_stock_products = self.get_queryset().filter(quantity__lt=F('min_stock'))
        context['low_stock_products'] = low_stock_products

        return context

class ProductUpdateView(LoginRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'myapp/edit_product.html'
    success_url = reverse_lazy('product_list')

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, _(f'تم تعديل المنتج {form.instance.product_name} بنجاح!'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("حدث خطأ في تعديل المنتج. يرجى التحقق من النموذج."))
        return super().form_invalid(form)

class ProductDeleteView(LoginRequiredMixin, DeleteView):
    model = Product
    template_name = 'myapp/delete_product_confirm.html'
    success_url = reverse_lazy('product_list')

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        product = self.get_object()
        messages.success(self.request, _(f'تم حذف المنتج {product.product_name} بنجاح!'))
        return super().delete(request, *args, **kwargs)

def add_product_warehouse_selection(request):
    if request.method == 'POST':
        form = WarehouseSelectionForm(request.POST)
        if form.is_valid():
            selected_warehouses = form.cleaned_data['warehouses']
            request.session['selected_warehouses'] = [warehouse.id for warehouse in selected_warehouses]
            return redirect('add_product_details')
    else:
        form = WarehouseSelectionForm()
    return render(request, 'myapp/add_product_warehouse_selection.html', {'form': form})

class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'myapp/add_product_details.html'
    success_url = reverse_lazy('product_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['selected_warehouses'] = self.request.session.get('selected_warehouses')
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.team = self.request.user.groups.first() if self.request.user.groups.exists() else None
        product = form.save()

        selected_warehouses = self.request.session.get('selected_warehouses', [])
        print(f"Selected Warehouses in form_valid: {selected_warehouses}")  # تسجيل المخازن المختارة

        for warehouse_id in selected_warehouses:
            warehouse_qty = form.cleaned_data.get(f'warehouse_qty_{warehouse_id}')
            if warehouse_qty is not None and warehouse_qty > 0:
                try:
                    warehouse = Warehouse.objects.get(pk=warehouse_id)
                    # التحقق إذا كان المنتج موجود بالفعل في هذا المخزن
                    if not ProductWarehouse.objects.filter(product=product, warehouse=warehouse).exists():
                        ProductWarehouse.objects.create(product=product, warehouse=warehouse, quantity=warehouse_qty)
                        Movement.objects.create(
                            product=product,
                            movement_type=_('استلام'),
                            quantity=warehouse_qty,
                            team=self.request.user.groups.first() if self.request.user.groups.exists() else None
                        )
                        product.quantity += Decimal(str(warehouse_qty))
                    else:
                        messages.warning(self.request, _(f'المنتج {product.product_name} موجود بالفعل في مخزن {warehouse.name}. لم يتم إضافة كمية إضافية.'))
                except Warehouse.DoesNotExist:
                    messages.error(self.request, _(f'المخزن برقم {warehouse_id} غير موجود.'))

        product.save()
        messages.success(self.request, _(f'تم إضافة المنتج {form.instance.product_name} بنجاح!'))

        users_in_team = User.objects.filter(groups=form.instance.team)
        for user in users_in_team:
            Notification.objects.create(
                user=user,
                notification_type='new_product',
                message=_(f'تم إضافة منتج جديد: {form.instance.product_name}.'),
                product=form.instance
            )

        # Clear the selected warehouses from the session
        if 'selected_warehouses' in self.request.session:
            del self.request.session['selected_warehouses']

        return redirect(self.success_url)

    def form_invalid(self, form):
        messages.error(self.request, _("حدث خطأ في إضافة المنتج. يرجى التحقق من النموذج."))
        return render(self.request, self.template_name, self.get_context_data(form=form))

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
    """
    عرض سجل الحركات مع معلومات المخزون (المخزنة في وقت الحركة)، مع تطبيق ترقيم الصفحات.
    """
    movements = Movement.objects.all().select_related('product', 'warehouse', 'team').order_by('-date')

    # استخدام Paginator لتقسيم النتائج
    paginator = Paginator(movements, 20)
    page = request.GET.get('page')
    try:
        movements_page = paginator.page(page)
    except PageNotAnInteger:
        movements_page = paginator.page(1)
    except EmptyPage:
        movements_page = paginator.page(paginator.num_pages)

    movements_with_stock_info = []
    for movement in movements_page:
        movements_with_stock_info.append({
            'movement': movement,
            'current_stock': movement.current_stock_at_movement,  # استخدم الحقل المخزن
            'total_stock_all_warehouses': movement.total_stock_at_movement,  # استخدم الحقل المخزن
        })

    context = {
        'movements_with_stock_info': movements_with_stock_info,
        'report_type': _('سجل الحركات'),
        'movements_page': movements_page,
    }
    return render(request, 'myapp/reports.html', context)


@login_required
def get_products_json(request):
    """
    إرجاع جميع المنتجات كـ JSON.
    """
    products = Product.objects.all().order_by('product_name').values('id', 'product_name', 'product_code')
    return JsonResponse(list(products), safe=False)


@login_required
def search_movements(request):
    """
    البحث عن الحركات بناءً على معايير متعددة، مع تطبيق ترقيم الصفحات.
    """
    product_query = request.GET.get('product_query')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    search_results_with_stock = []
    q_objects = Q()

    if product_query:
        q_objects &= Q(product_id=product_query)

    if start_date_str:
        try:
            start_date = timezone.make_aware(datetime.strptime(start_date_str, '%Y-%m-%d')).date()
            q_objects &= Q(date__gte=start_date)
        except ValueError:
            pass

    if end_date_str:
        try:
            end_date = timezone.make_aware(datetime.strptime(end_date_str, '%Y-%m-%d')).date()
            q_objects &= Q(date__lte=end_date)
        except ValueError:
            pass

    if q_objects:
        search_results = Movement.objects.filter(q_objects).select_related('product', 'warehouse', 'team').order_by('-date')
    else:
        search_results = Movement.objects.none()

    paginator = Paginator(search_results, 20)
    page = request.GET.get('page')
    try:
        search_results_page = paginator.page(page)
    except PageNotAnInteger:
        search_results_page = paginator.page(1)
    except EmptyPage:
        search_results_page = paginator.page(paginator.num_pages)

    for movement in search_results_page:
        search_results_with_stock.append({
            'movement': movement,
            'current_stock': movement.current_stock_at_movement,  # استخدم الحقل المخزن
            'total_stock_all_warehouses': movement.total_stock_at_movement,  # استخدم الحقل المخزن
        })

    context = {
        'search_results': search_results_with_stock,
        'search_results_page': search_results_page,
    }
    return render(request, 'myapp/reports.html', context)

@login_required
def search_movements_excel(request):
    """
    تصدير نتائج البحث إلى Excel.
    """
    product_query = request.GET.get('product_query')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()

    header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D3D3D3', 'border': 1})
    cell_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})

    columns = [
        _('#'),
        _('اسم المنتج'),
        _('نوع الحركة'),
        _('الكمية'),
        _('الوحدة'),
        _('التاريخ'),
        _('المخزن'),
        _('الرصيد الحالي بالمخزن'),
        _('الرصيد الكلي بكل المخازن'),
        _('الفريق'),
    ]
    worksheet.write_row(0, 0, columns, header_format)

    q_objects = Q()
    if product_query:
        q_objects &= Q(product_id=product_query)

    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            q_objects &= Q(date__gte=start_date)
        except ValueError:
            pass
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            q_objects &= Q(date__lte=end_date)
        except ValueError:
            pass

    if q_objects:
        search_results = Movement.objects.filter(q_objects).select_related('product', 'warehouse', 'team').order_by('-date')
    else:
        search_results = Movement.objects.none()

    row_num = 1
    for index, movement in enumerate(search_results):
        row_data = [
            index + 1,
            movement.product.product_name,
            _('استلام') if movement.movement_type == 'استلام' else _('سحب'),
            movement.quantity,
            movement.product.unit,
            movement.date.strftime('%Y-%m-%d %H:%M:%S'),
            movement.warehouse.name,
            movement.current_stock_at_movement,  # استخدم الحقل المخزن
            movement.total_stock_at_movement,  # استخدم الحقل المخزن
            movement.team.name,
        ]
        worksheet.write_row(row_num, 0, row_data, cell_format)
        row_num += 1

    worksheet.set_column(0, len(columns) - 1, 15)
    workbook.close()
    output.seek(0)

    response = HttpResponse(content=output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="search_results.xlsx"'
    return response

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
    if request.method == 'POST' and 'select_product' in request.POST:
        product_id = request.POST.get('product_id')
        product = get_object_or_404(Product, pk=product_id, team__in=request.user.groups.all())

        add_form = AddQuantityToWarehousesForm(
            product=product,
            initial={'product_id': product_id, 'total_quantity_to_add': request.POST.get('quantity_to_add')}
        )
        context = {
            'add_form': add_form,
            'product': product,
            'quantity_to_add': request.POST.get('quantity_to_add'),
        }
        return render(request, 'myapp/add_quantity_warehouses.html', context)

    elif request.method == 'POST' and 'add_to_warehouses' in request.POST:
        print("Data received in add_to_warehouses POST request:")
        print(request.POST)
        product_id = request.POST.get('product_id')
        product = get_object_or_404(Product, pk=product_id, team__in=request.user.groups.all())
        form = AddQuantityToWarehousesForm(request.POST, product=product)
        if form.is_valid():
            print("Add form is valid!")
            print(form.cleaned_data)
            total_quantity_to_add = Decimal(str(form.cleaned_data['total_quantity_to_add']))
            added_quantity = Decimal('0.00')

            for warehouse in Warehouse.objects.all():
                quantity_to_add_warehouse = form.cleaned_data.get(f'warehouse_{warehouse.id}')
                if quantity_to_add_warehouse and quantity_to_add_warehouse > 0:
                    try:
                        product_warehouse = ProductWarehouse.objects.get(product=product, warehouse=warehouse)
                        # احفظ الرصيد الحالي قبل الإضافة
                        stock_before_add = product_warehouse.quantity
                        product_warehouse.quantity += quantity_to_add_warehouse
                        product_warehouse.save()
                        print(f"Added {quantity_to_add_warehouse} to {warehouse.name} for {product.product_name}. New quantity: {product_warehouse.quantity}")

                        # === إنشاء الحركة هنا لكل إضافة في مخزن ===
                        Movement.objects.create(
                            product=product,
                            warehouse=warehouse,
                            movement_type='استلام',
                            quantity=quantity_to_add_warehouse,
                            team=product.team,
                            current_stock_at_movement=stock_before_add, # استخدم الرصيد قبل الإضافة
                            total_stock_at_movement=ProductWarehouse.objects.filter(product=product).aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0.00') # احسب الرصيد الكلي بعد الإضافة
                        )
                        print(f"تم إنشاء حركة استلام لـ {product.product_name} في {warehouse.name} بكمية {quantity_to_add_warehouse}")
                        # === نهاية إنشاء الحركة ===

                    except ProductWarehouse.DoesNotExist:
                        ProductWarehouse.objects.create(product=product, warehouse=warehouse, quantity=quantity_to_add_warehouse)
                        # في حالة الإنشاء، الرصيد قبل الإضافة كان صفر
                        Movement.objects.create(
                            product=product,
                            warehouse=warehouse,
                            movement_type='استلام',
                            quantity=quantity_to_add_warehouse,
                            team=product.team,
                            current_stock_at_movement=Decimal('0.00'),
                            total_stock_at_movement=ProductWarehouse.objects.filter(product=product).aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0.00')
                        )
                        print(f"Created {product.product_name} in {warehouse.name} with quantity: {quantity_to_add_warehouse}")

                    added_quantity += quantity_to_add_warehouse

            # تحديث الكمية الكلية للمنتج بعد معالجة كل المخازن
            total_quantity = Decimal('0.00')
            for pw in product.productwarehouse_set.all():
                total_quantity += pw.quantity
            product.quantity = total_quantity
            product.save()

            # === إضافة إنشاء الإشعار للفريق ===
            users_in_team = User.objects.filter(groups=product.team)
            for user in users_in_team:
                Notification.objects.create(
                    user=user,
                    notification_type='quantity_added',
                    message=_(f'تمت إضافة {total_quantity_to_add} وحدة إلى المنتج {product.product_name}.'),
                    product=product
                )
            # === نهاية إضافة الإشعار ===

            if added_quantity == total_quantity_to_add:
                messages.success(request, _(f"تمت إضافة {total_quantity_to_add} بنجاح إلى المخازن المحددة لـ {product.product_name}."))
                return redirect('product_list')
            else:
                messages.warning(request, _(f"تمت إضافة {added_quantity} بدلًا من {total_quantity_to_add}. الرجاء التحقق."))
                return redirect('product_list')

        else:
            print("Add form is NOT valid!")
            print(form.errors)
            messages.error(request, _("حدث خطأ في البيانات المدخلة. الرجاء التأكد من صحة البيانات."))
            return redirect('add_quantity')

    products_with_availability = []
    products = Product.objects.filter(team__in=request.user.groups.all())
    for product in products:
        total_quantity_in_warehouses = ProductWarehouse.objects.filter(product=product).aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0.00')
        products_with_availability.append({
            'id': product.id,
            'product_name': product.product_name,
            'product_code': product.product_code,
            'unit': product.unit,
            'available_quantity': total_quantity_in_warehouses,
        })

    context = {
        'products': products_with_availability,
    }
    return render(request, 'myapp/add_quantity.html', context)


# تقرير الكميات المستلمة (Excel) (تعديل لعرض فقط حركات منتجات المستخدم)
@login_required
def received_report_excel(request):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()

    # تنسيقات الخلايا
    header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D3D3D3', 'border': 1})
    cell_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})

    # عناوين الأعمدة (نفس الأعمدة اللي في الجدول)
    columns = [
        _('#'),
        _('اسم المنتج'),
        _('الكمية المستلمة'),
        _('الوحدة'),
        _('التاريخ'),
        _('المخزن'),
        _('الرصيد الحالي بالمخزن'),
        _('الرصيد الكلي بكل المخازن'),
        _('الفريق'),
    ]
    worksheet.write_row(0, 0, columns, header_format)

    received_movements = Movement.objects.filter(
        movement_type='استلام'
        # هنشيل الفلتر بتاع الفريق عشان يجيب كل حركات الاستلام
    ).select_related('product', 'warehouse', 'team').order_by('-date')

    row_num = 1
    for index, movement in enumerate(received_movements):
        try:
            product_warehouse = ProductWarehouse.objects.get(
                product=movement.product,
                warehouse=movement.warehouse
            )
            current_stock = product_warehouse.quantity
        except ProductWarehouse.DoesNotExist:
            current_stock = Decimal('0.00')

        total_stock_all_warehouses = ProductWarehouse.objects.filter(
            product=movement.product
        ).aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0.00')

        row_data = [
            index + 1,
            movement.product.product_name,
            movement.quantity,
            movement.product.unit,
            movement.date.strftime('%Y-%m-%d %H:%M:%S'),
            movement.warehouse.name,
            current_stock,
            total_stock_all_warehouses,
            movement.team.name,
        ]
        worksheet.write_row(row_num, 0, row_data, cell_format)
        row_num += 1

    # ضبط عرض الأعمدة
    worksheet.set_column(0, len(columns) - 1, 15)

    workbook.close()
    output.seek(0)

    response = HttpResponse(content=output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="received_report.xlsx"'
    return response

@login_required
def withdraw_quantity(request):
    if request.method == 'POST' and 'select_product' in request.POST:
        product_id = request.POST.get('product_id')
        quantity_to_withdraw = request.POST.get('quantity_to_withdraw')  # استقبل الكمية
        product = get_object_or_404(Product, pk=product_id, team__in=request.user.groups.all())

        # مرر الكمية المراد سحبها كـ initial value للفورم
        withdraw_form = WithdrawQuantityFromWarehousesForm(
            product=product,
            initial={'product_id': product_id, 'total_quantity_to_withdraw': quantity_to_withdraw}
        )
        context = {
            'withdraw_form': withdraw_form,
            'product': product,
            'quantity_to_withdraw': quantity_to_withdraw, # ابعتها كمان للكونتيكست عشان نعرضها في الصفحة الجديدة
        }
        return render(request, 'myapp/withdraw_quantity_warehouses.html', context)

    elif request.method == 'POST' and 'withdraw_from_warehouses' in request.POST:
        print("Data received in withdraw_from_warehouses POST request:")  # <--- Print دي
        print(request.POST)  # <--- Print دي
        product_id = request.POST.get('product_id')  # Get the product ID from the POST data
        product = get_object_or_404(Product, pk=product_id, team__in=request.user.groups.all()) # Get the correct product
        form = WithdrawQuantityFromWarehousesForm(request.POST, product=product) # Pass the correct product to the form
        if form.is_valid():
            print("Form is valid!") # <--- Print دي
            print(form.cleaned_data) # <--- السطر اللي كان ناقص!
            total_quantity_to_withdraw = Decimal(str(form.cleaned_data['total_quantity_to_withdraw']))
            print(f"Product ID: {product_id}") # <--- Print دي
            print(f"Total Quantity to Withdraw: {total_quantity_to_withdraw}") # <--- Print دي
            withdrawn_quantity = Decimal('0.00')

            for warehouse in Warehouse.objects.filter(productwarehouse__product=product):
                quantity_to_withdraw_warehouse = form.cleaned_data.get(f'warehouse_{warehouse.id}')
                print(f"Warehouse ID: {warehouse.id}")  # <--- السطر اللي هنضيفه
                print(f"Quantity from form for warehouse {warehouse.id}: {quantity_to_withdraw_warehouse}") # <--- السطر اللي هنضيفه
                if quantity_to_withdraw_warehouse and quantity_to_withdraw_warehouse > 0:
                    product_warehouse = get_object_or_404(ProductWarehouse, product=product, warehouse=warehouse)
                    quantity_to_withdraw_decimal = Decimal(str(quantity_to_withdraw_warehouse))
                    if product_warehouse.quantity >= quantity_to_withdraw_decimal:
                        product_warehouse.quantity -= quantity_to_withdraw_decimal
                        product_warehouse.save()

                        total_quantity = Decimal('0.00')
                        for pw in product.productwarehouse_set.all():
                            total_quantity += pw.quantity
                        product.quantity = total_quantity
                        product.save()

                        # === إنشاء الحركة هنا لكل سحب من مخزن ===
                        Movement.objects.create(
                            product=product,
                            warehouse=warehouse,
                            movement_type='سحب',
                            quantity=quantity_to_withdraw_decimal,
                            team=product.team,
                            stock_after_movement=total_quantity # سجل الكمية الكلية بعد السحب
                        )
                        print(f"تم إنشاء حركة سحب لـ {product.product_name} من {warehouse.name} بكمية {quantity_to_withdraw_decimal}")
                        # === نهاية إنشاء الحركة ===

                        withdrawn_quantity += quantity_to_withdraw_decimal

                    else:
                        messages.error(request, _(f"الكمية المطلوبة للسحب من {warehouse.name} غير متوفرة."))
                        return redirect('withdraw_quantity')

            if withdrawn_quantity == total_quantity_to_withdraw:
                messages.success(request, _(f"تم سحب {total_quantity_to_withdraw} بنجاح من المخازن المحددة لـ {product.product_name}."))
                return redirect('product_list')
            else:
                messages.warning(request, _(f"تم سحب {withdrawn_quantity} بدلًا من {total_quantity_to_withdraw}. الرجاء التحقق."))
                return redirect('product_list') # أو صفحة تفاصيل الحركة

        else:
            print("Form is NOT valid!") # <--- Print دي
            print(form.errors) # <--- Print دي
            messages.error(request, _("حدث خطأ في البيانات المدخلة. الرجاء التأكد من صحة البيانات."))
            return redirect('withdraw_quantity')

    products_with_availability = []
    products = Product.objects.filter(team__in=request.user.groups.all())
    for product in products:
        total_quantity_in_warehouses = ProductWarehouse.objects.filter(product=product).aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0.00')
        products_with_availability.append({
            'id': product.id,
            'product_name': product.product_name,
            'product_code': product.product_code,
            'unit': product.unit,
            'available_quantity': total_quantity_in_warehouses,
        })

    context = {
        'products': products_with_availability,
    }
    return render(request, 'myapp/withdraw_quantity.html', context)
@login_required
def withdrawn_report_excel(request):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()

    # تنسيقات الخلايا
    header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D3D3D3', 'border': 1})
    cell_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})

    # عناوين الأعمدة (نفس الأعمدة اللي في جدول الاستلام مع تغيير الاسم)
    columns = [
        _('#'),
        _('اسم المنتج'),
        _('الكمية المسحوبة'),
        _('الوحدة'),
        _('التاريخ'),
        _('المخزن'),
        _('الرصيد الحالي بالمخزن'),
        _('الرصيد الكلي بكل المخازن'),
        _('الفريق'),
    ]
    worksheet.write_row(0, 0, columns, header_format)

    withdrawn_movements = Movement.objects.filter(
        movement_type='سحب',
        product__team__in=request.user.groups.all()
    ).select_related('product', 'warehouse', 'team').order_by('-date')

    row_num = 1
    for index, movement in enumerate(withdrawn_movements):
        try:
            product_warehouse = ProductWarehouse.objects.get(
                product=movement.product,
                warehouse=movement.warehouse
            )
            current_stock = product_warehouse.quantity
        except ProductWarehouse.DoesNotExist:
            current_stock = Decimal('0.00')

        total_stock_all_warehouses = ProductWarehouse.objects.filter(
            product=movement.product
        ).aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0.00')

        row_data = [
            index + 1,
            movement.product.product_name,
            movement.quantity,
            movement.product.unit,
            movement.date.strftime('%Y-%m-%d %H:%M:%S'),
            movement.warehouse.name,
            current_stock,
            total_stock_all_warehouses,
            movement.team.name,
        ]
        worksheet.write_row(row_num, 0, row_data, cell_format)
        row_num += 1

    # ضبط عرض الأعمدة
    worksheet.set_column(0, len(columns) - 1, 15)

    workbook.close()
    output.seek(0)

    response = HttpResponse(content=output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="withdrawn_report.xlsx"'
    return response

@login_required
def chart_view(request):
    # تعريف الوحدات لقسم المواد الخام
    raw_material_units = ['טון', 'ק"ג', 'לי']
    # تعريف الوحدات لقسم الأوراق/التغليف
    packaging_units = ['שק', "יח'"]

    # استعلام للمنتجات المسحوبة في قسم المواد الخام
    raw_material_data = Movement.objects.filter(
        movement_type='سحب',
        product__team__in=request.user.groups.all(),
        product__unit__in=raw_material_units
    ).values('product__product_name').annotate(total_quantity=Sum('quantity')).order_by('-total_quantity')

    # استعلام للمنتجات المسحوبة في قسم الأوراق/التغليف
    packaging_data = Movement.objects.filter(
        movement_type='سحب',
        product__team__in=request.user.groups.all(),
        product__unit__in=packaging_units
    ).values('product__product_name').annotate(total_quantity=Sum('quantity')).order_by('-total_quantity')

    context = {
        'raw_material_data': raw_material_data,
        'packaging_data': packaging_data,
        'raw_material_units': raw_material_units,
        'packaging_units': packaging_units,
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
    products = Product.objects.filter(user=request.user).prefetch_related('warehouses') # لتحسين الأداء
    data = {
        _('اسم المنتج'): [product.product_name for product in products],
        _('رمز المنتج'): [product.product_code for product in products],
        _('الكمية'): [product.quantity for product in products],
        _('الوحدة'): [product.unit for product in products], # ممكن تحتاج ترجمة قيم الوحدات هنا كمان
        _('الحد الأدنى'): [product.min_stock for product in products],
        _('المخازن'): [', '.join([warehouse.name for warehouse in product.warehouses.all()]) for product in products],
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

    # === إضافة إنشاء الإشعار للمستخدم الحالي ===
    if low_stock.exists():
        Notification.objects.create(
            user=request.user,
            notification_type='low_stock_report',
            message=_(f'انتبه! يوجد {low_stock.count()} منتج في حالة نقص بالمخزون.'),
        )
    # === نهاية إضافة الإشعار ===

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
        required_columns = ['product_name', 'product_code', 'unit', 'min_stock', 'quantity']

        if not all(col in df.columns for col in required_columns):
            messages.error(request, _('خطأ: ملف Excel لا يحتوي على جميع الأعمدة المطلوبة (اسم المنتج، الرمز، الوحدة، الحد الأدنى، الكمية).'))
            return redirect('product_list')

        # **استخلاص أسماء المخازن من الصف الأول (بعد الأعمدة الأساسية)**
        warehouse_names_from_excel = [col.strip() for col in df.columns if col not in required_columns]

        current_user_team = request.user.groups.first()
        if not current_user_team:
            messages.error(request, _('خطأ: المستخدم الحالي ليس لديه فريق محدد.'))
            return redirect('product_list')

        for index, row in df.iterrows():
            try:
                product = Product.objects.create(
                    user=request.user,
                    team=current_user_team,
                    product_name=row['product_name'],
                    product_code=row['product_code'],
                    unit=row['unit'],
                    min_stock=row['min_stock'],
                    quantity=row['quantity']
                )
                warehouses_with_quantity = {}
                # **ربط الكميات بأسماء المخازن من الإكسل**
                for warehouse_name_excel in warehouse_names_from_excel:
                    warehouse_quantity = row.get(warehouse_name_excel)
                    if pd.notna(warehouse_quantity) and warehouse_quantity > 0:
                        try:
                            # **محاولة الحصول على المخزن الموجود بالاسم**
                            warehouse = Warehouse.objects.get(name=warehouse_name_excel)
                            ProductWarehouse.objects.create(
                                product=product,
                                warehouse=warehouse,
                                quantity=warehouse_quantity
                            )
                            warehouses_with_quantity[warehouse_name_excel] = warehouse_quantity
                        except Warehouse.DoesNotExist:
                            # **خيار إنشاء المخزن تلقائيًا:**
                            warehouse, created = Warehouse.objects.get_or_create(name=warehouse_name_excel)
                            ProductWarehouse.objects.create(
                                product=product,
                                warehouse=warehouse,
                                quantity=warehouse_quantity
                            )
                            if created:
                                messages.info(request, _(f'تم إنشاء مخزن جديد "{warehouse_name_excel}".'))
                            else:
                                messages.warning(request, _(f'تحذير: لم يتم العثور على المخزن "{warehouse_name_excel}" وتم ربط الكمية به.'))


                if warehouses_with_quantity:
                    warehouses_str = ', '.join(warehouses_with_quantity.keys())
                    messages.success(request, _(f'تم استيراد المنتج {product.product_name} ({product.product_code}) وتوزيعه على المخازن: {warehouses_str} بنجاح.'))
                else:
                    messages.info(request, _(f'تم رفع المنتج {product.product_name} ({product.product_code}) لكنه غير موجود في أي من المخازن في هذا الصف.'))

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
        required_columns = ['product_name', 'product_code', 'unit', 'min_stock', 'quantity']

        if not all(col in df.columns for col in required_columns):
            messages.error(request, _('خطأ: ملف Excel لا يحتوي على جميع الأعمدة المطلوبة (اسم المنتج، الرمز، الوحدة، الحد الأدنى، الكمية).'))
            return redirect('product_list')

        # **استخلاص أسماء المخازن من الصف الأول (بعد الأعمدة الأساسية)**
        warehouse_names_from_excel = [col.strip() for col in df.columns if col not in required_columns]

        raw_materials_team = Group.objects.filter(name='فريق المواد الخام').first()
        if not raw_materials_team:
            messages.error(request, _('خطأ: لم يتم العثور على فريق "فريق المواد الخام".'))
            return redirect('product_list')

        for index, row in df.iterrows():
            try:
                product = Product.objects.create(
                    user=request.user,
                    team=raw_materials_team,
                    product_name=row['product_name'],
                    product_code=row['product_code'],
                    unit=row['unit'],
                    min_stock=row['min_stock'],
                    quantity=row['quantity']
                )
                warehouses_with_quantity = {}
                # **ربط الكميات بأسماء المخازن من الإكسل**
                for warehouse_name_excel in warehouse_names_from_excel:
                    warehouse_quantity = row.get(warehouse_name_excel)
                    if pd.notna(warehouse_quantity) and warehouse_quantity > 0:
                        try:
                            # **محاولة الحصول على المخزن الموجود بالاسم**
                            warehouse = Warehouse.objects.get(name=warehouse_name_excel)
                            ProductWarehouse.objects.create(
                                product=product,
                                warehouse=warehouse,
                                quantity=warehouse_quantity
                            )
                            warehouses_with_quantity[warehouse_name_excel] = warehouse_quantity
                        except Warehouse.DoesNotExist:
                            # **خيار إنشاء المخزن تلقائيًا:**
                            warehouse, created = Warehouse.objects.get_or_create(name=warehouse_name_excel)
                            ProductWarehouse.objects.create(
                                product=product,
                                warehouse=warehouse,
                                quantity=warehouse_quantity
                            )
                            if created:
                                messages.info(request, _(f'تم إنشاء مخزن جديد "{warehouse_name_excel}".'))
                            else:
                                messages.warning(request, _(f'تحذير: لم يتم العثور على المخزن "{warehouse_name_excel}" وتم ربط الكمية به.'))

                if warehouses_with_quantity:
                    warehouses_str = ', '.join(warehouses_with_quantity.keys())
                    messages.success(request, _(f'تم استيراد منتج المواد الخام {product.product_name} ({product.product_code}) وتوزيعه على المخازن: {warehouses_str} بنجاح.'))
                else:
                    messages.info(request, _(f'تم رفع منتج المواد الخام {product.product_name} ({product.product_code}) لكنه غير موجود في أي من المخازن في هذا الصف.'))

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
        required_columns = ['product_name', 'product_code', 'unit', 'min_stock', 'quantity']

        if not all(col in df.columns for col in required_columns):
            messages.error(request, _('خطأ: ملف Excel لا يحتوي على جميع الأعمدة المطلوبة (اسم المنتج، الرمز، الوحدة، الحد الأدنى، الكمية).'))
            return redirect('product_list')

        # **استخلاص أسماء المخازن من الصف الأول (بعد الأعمدة الأساسية)**
        warehouse_names_from_excel = [col.strip() for col in df.columns if col not in required_columns]

        maintenance_team = Group.objects.filter(name='فريق الصيانة').first()
        if not maintenance_team:
            messages.error(request, _('خطأ: لم يتم العثور على فريق "فريق الصيانة".'))
            return redirect('product_list')

        for index, row in df.iterrows():
            try:
                product = Product.objects.create(
                    user=request.user,
                    team=maintenance_team,
                    product_name=row['product_name'],
                    product_code=row['product_code'],
                    unit=row['unit'],
                    min_stock=row['min_stock'],
                    quantity=row['quantity']
                )
                warehouses_with_quantity = {}
                # **ربط الكميات بأسماء المخازن من الإكسل**
                for warehouse_name_excel in warehouse_names_from_excel:
                    warehouse_quantity = row.get(warehouse_name_excel)
                    if pd.notna(warehouse_quantity) and warehouse_quantity > 0:
                        try:
                            # **محاولة الحصول على المخزن الموجود بالاسم**
                            warehouse = Warehouse.objects.get(name=warehouse_name_excel)
                            ProductWarehouse.objects.create(
                                product=product,
                                warehouse=warehouse,
                                quantity=warehouse_quantity
                            )
                            warehouses_with_quantity[warehouse_name_excel] = warehouse_quantity
                        except Warehouse.DoesNotExist:
                            # **خيار إنشاء المخزن تلقائيًا:**
                            warehouse, created = Warehouse.objects.get_or_create(name=warehouse_name_excel)
                            ProductWarehouse.objects.create(
                                product=product,
                                warehouse=warehouse,
                                quantity=warehouse_quantity
                            )
                            if created:
                                messages.info(request, _(f'تم إنشاء مخزن جديد "{warehouse_name_excel}".'))
                            else:
                                messages.warning(request, _(f'تحذير: لم يتم العثور على المخزن "{warehouse_name_excel}" وتم ربط الكمية به.'))

                if warehouses_with_quantity:
                    warehouses_str = ', '.join(warehouses_with_quantity.keys())
                    messages.success(request, _(f'تم استيراد منتج الصيانة {product.product_name} ({product.product_code}) وتوزيعه على المخازن: {warehouses_str} بنجاح.'))
                else:
                    messages.info(request, _(f'تم رفع منتج الصيانة {product.product_name} ({product.product_code}) لكنه غير موجود في أي من المخازن في هذا الصف.'))

            except Exception as e:
                messages.error(request, _(f'خطأ في استيراد الصف {index + 2}: {e}'))
                return redirect(request.META.get('HTTP_REFERER', 'product_list'))

        messages.success(request, _('تم استيراد منتجات الصيانة بنجاح.'))
        return redirect(request.META.get('HTTP_REFERER', 'product_list'))
    return render(request, 'myapp/import_excel.html', {'import_type': 'maintenance'})

def view_product_details(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product_warehouses = ProductWarehouse.objects.filter(product=product).select_related('warehouse')
    context = {
        'product': product,
        'product_warehouses': product_warehouses,
    }
    return render(request, 'myapp/product_details.html', context)
