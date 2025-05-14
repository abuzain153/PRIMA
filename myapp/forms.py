from django import forms
from .models import Product, Warehouse, ProductWarehouse
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import PasswordResetForm, UserCreationForm
from django.contrib.auth.models import User, Group
from django.core.mail import send_mail
from django.template.loader import render_to_string
from decimal import Decimal, DecimalException


class WarehouseSelectionForm(forms.Form):
    warehouses = forms.ModelMultipleChoiceField(
        queryset=Warehouse.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label=_('اختر المخازن')
    )


class ProductForm(forms.ModelForm):
    product_name = forms.CharField(label=_('اسم المنتج'))
    product_code = forms.CharField(label=_('رمز المنتج'))
    quantity = forms.DecimalField(
        label=_('الكمية الكلية المتاحة'),
        widget=forms.NumberInput(attrs={'step': 'any'}),
        required=False,
        decimal_places=2  # هنخليها عشان الداتا تتخزن بخانتين
    )
    unit = forms.CharField(label=_('الوحدة'))
    min_stock = forms.IntegerField(label=_('الحد الأدنى للمخزون'))
    # هنشيل warehouses_quantities من هنا
    warehouse_quantities = forms.CharField(widget=forms.HiddenInput(), required=False)  # هنستخدمه لتمرير بيانات الكميات

    def __init__(self, *args, selected_warehouses=None, initial_quantities=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.warehouse_fields = {}
        if initial_quantities is None:
            initial_quantities = {}

        # لو فيه مخازن مختارة، هنعرض ليها خانات كمية
        if selected_warehouses:
            for warehouse_id in selected_warehouses:
                try:
                    warehouse = Warehouse.objects.get(pk=warehouse_id)
                    field_name = f'warehouse_qty_{warehouse.id}'
                    self.fields[field_name] = forms.FloatField(
                        label=f'{warehouse.name} {_("الكمية")}',
                        required=True,
                        widget=forms.NumberInput(attrs={'step': 'any'}),
                        initial=initial_quantities.get(warehouse.id, 0)
                    )
                    self.warehouse_fields[warehouse.id] = field_name
                except Warehouse.DoesNotExist:
                    pass  # ممكن نعالج دي بطريقة تانية لو ضروري
        else:
            # لما بنعدل منتج موجود، نعرض كل خانات المخازن مع قيمها
            if self.instance.pk:
                product_warehouses = ProductWarehouse.objects.filter(product=self.instance)
                initial_quantities = {pw.warehouse_id: pw.quantity for pw in product_warehouses}
                if self.instance.quantity == self.instance.quantity.to_integral_value():
                    self.fields['quantity'].initial = int(self.instance.quantity)
                else:
                    self.fields['quantity'].initial = format(self.instance.quantity, '.2f')
                for warehouse in Warehouse.objects.all():
                    field_name = f'warehouse_qty_{warehouse.id}'
                    self.fields[field_name] = forms.FloatField(
                        label=f'{warehouse.name} {_("الكمية")}',
                        required=False,
                        widget=forms.NumberInput(attrs={'step': 'any'}),
                        initial=initial_quantities.get(warehouse.id, 0)
                    )
                    self.warehouse_fields[warehouse.id] = field_name
            else:
                self.fields['quantity'].initial = 0

    class Meta:
        model = Product
        fields = ['product_name', 'product_code', 'quantity', 'unit', 'min_stock']

    def clean(self):
        cleaned_data = super().clean()
        total_quantity = Decimal('0.00')
        warehouse_quantities = {}
        for warehouse_id, field_name in self.warehouse_fields.items():
            quantity = cleaned_data.get(field_name)
            if quantity is not None:
                total_quantity += Decimal(str(quantity))
                warehouse_quantities[warehouse_id] = quantity
        cleaned_data['quantity'] = total_quantity
        cleaned_data['warehouses_quantities'] = warehouse_quantities
        return cleaned_data

    def clean_quantity(self):
        return self.cleaned_data.get('quantity', Decimal('0.00'))

    def clean_min_stock(self):
        min_stock = self.cleaned_data['min_stock']
        if min_stock <= 0:
            raise forms.ValidationError(_("الحد الأدنى يجب أن يكون أكبر من صفر."))
        return min_stock

    def clean_product_code(self):
        product_code = self.cleaned_data['product_code']
        if self.instance:
            if Product.objects.filter(product_code=product_code).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError(_("رمز المنتج موجود بالفعل."))
        else:
            if Product.objects.filter(product_code=product_code).exists():
                raise forms.ValidationError(_("رمز المنتج موجود بالفعل."))
        return product_code

    def save(self, commit=True):
        product = super().save(commit=commit)
        if commit:
            warehouse_quantities = self.cleaned_data.get('warehouses_quantities', {})
            ProductWarehouse.objects.filter(product=product).delete()
            for warehouse_id, quantity in warehouse_quantities.items():
                if quantity is not None and quantity > 0:
                    warehouse = Warehouse.objects.get(pk=warehouse_id)
                    ProductWarehouse.objects.create(product=product, warehouse=warehouse, quantity=quantity)
        return product


class ForgetPasswordForm(PasswordResetForm):
    email = forms.EmailField(label=_('البريد الإلكتروني'))

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email=None, html_email_template_name=None):
        subject = render_to_string(subject_template_name, context)
        subject = ''.join(subject.splitlines())
        body = render_to_string(email_template_name, context)
        html_body = render_to_string(html_email_template_name, context) if html_email_template_name else None
        send_mail(subject, body, from_email, [context['email']], html_message=html_body)


class WithdrawQuantityFromWarehousesForm(forms.Form):
    def __init__(self, *args, **kwargs):
        product = kwargs.pop('product', None)
        super().__init__(*args, **kwargs)
        if product:
            product_warehouses = ProductWarehouse.objects.filter(product=product)
            for pw in product_warehouses:
                self.fields[f'warehouse_{pw.warehouse.id}'] = forms.FloatField(
                    label=f"{pw.warehouse.name} ({_('المتاح')}: {pw.quantity})",
                    min_value=0.0,
                    required=False,
                    widget=forms.NumberInput(attrs={'class': 'form-control'})
                )

    total_quantity_to_withdraw = forms.FloatField(
        label=_('الكمية الكلية المراد سحبها'),
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'style': 'width: 150px; background-color: #f8d7da;'}),
        required=True
    )
    product_id = forms.IntegerField(widget=forms.HiddenInput())

    def clean(self):
        cleaned_data = super().clean()
        total_withdrawn = Decimal('0.0')
        for name, value in cleaned_data.items():  # هنلف على الـ items عشان نوصل للاسم والقيمة
            if name.startswith('warehouse_'):
                if value is not None:
                    try:
                        total_withdrawn += Decimal(str(value))
                    except DecimalException:
                        raise forms.ValidationError(_(f"أدخل قيمة رقمية صحيحة للمخزن {name.split('_')[1]}."))

        total_requested = cleaned_data.get('total_quantity_to_withdraw', Decimal('0.0'))
        print(f"Total Withdrawn (from form): {total_withdrawn}")
        print(f"Total Requested (from form): {total_requested}")

        if total_withdrawn > total_requested:
            raise forms.ValidationError(_("إجمالي الكمية المسحوبة من المخازن يتجاوز الكمية المطلوبة."))
        return cleaned_data


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(label=_('البريد الإلكتروني'))
    team = forms.ModelChoiceField(queryset=Group.objects.all(), empty_label=_("اختر فريقك"), label=_("الفريق"))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email', 'team')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        team = self.cleaned_data['team']
        if commit:
            user.save()
            user.groups.add(team)
        return user


class AddQuantityToWarehousesForm(forms.Form):
    total_quantity_to_add = forms.DecimalField(
        label=_('إجمالي الكمية المراد إضافتها'),
        min_value=Decimal('0.01'),
        decimal_places=2,
        required=True,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'style': 'width: 150px; background-color: #e3f2fd;'})
    )
    product_id = forms.IntegerField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        product = kwargs.pop('product', None)
        super().__init__(*args, **kwargs)
        if product:
            product_warehouses = ProductWarehouse.objects.filter(product=product)
            warehouses = Warehouse.objects.all()

            for warehouse in warehouses:
                try:
                    pw = product_warehouses.get(warehouse=warehouse)
                    current_quantity = pw.quantity
                except ProductWarehouse.DoesNotExist:
                    current_quantity = Decimal('0.00')

                self.fields[f'warehouse_{warehouse.id}'] = forms.DecimalField(
                    label=f"{warehouse.name} ({_('المتاح')}: {current_quantity})",
                    min_value=Decimal('0.00'),
                    decimal_places=2,
                    required=False,
                    initial=None  # <--- القيمة الصحيحة هي None
                )

    def clean(self):
        cleaned_data = super().clean()
        total_added = Decimal('0.00')
        for name, value in cleaned_data.items():
            if name.startswith('warehouse_'):
                if value is not None:
                    total_added += value

        total_quantity_to_add = cleaned_data.get('total_quantity_to_add')
        if total_quantity_to_add is not None and total_added != total_quantity_to_add:
            raise forms.ValidationError(_("إجمالي الكميات المضافة للمخازن يجب أن يساوي الكمية المراد إضافتها."))
        return cleaned_data

    def get_warehouse_quantities(self):
        warehouse_quantities = {}
        for name, value in self.cleaned_data.items():
            if name.startswith('warehouse_'):
                warehouse_id = name.split('_')[1]
                warehouse_quantities[warehouse_id] = value
        return warehouse_quantities
