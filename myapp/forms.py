class WithdrawQuantityFromWarehousesForm(forms.Form):
    total_quantity_to_withdraw = forms.DecimalField(
        label=_('الكمية الكلية المراد سحبها'),
        min_value=Decimal('0.01'),
        decimal_places=4,  # رفع الخانات العشرية
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly',
            'style': 'width: 150px; background-color: #f8d7da;',
            'step': '0.0001'  # يسمح بأربع خانات عشرية
        }),
        required=True
    )
    product_id = forms.IntegerField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        product = kwargs.pop('product', None)
        super().__init__(*args, **kwargs)
        self.warehouse_fields = []
        if product:
            product_warehouses = ProductWarehouse.objects.filter(product=product)
            for pw in product_warehouses:
                field_name = f'warehouse_{pw.warehouse.id}'
                self.fields[field_name] = forms.DecimalField(
                    label=f"{pw.warehouse.name} ({_('المتاح')}: {pw.quantity})",
                    min_value=Decimal('0.0'),
                    decimal_places=4,  # رفع الخانات العشرية
                    required=False,
                    widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'})
                )
                self.warehouse_fields.append(field_name)

    def clean(self):
        cleaned_data = super().clean()
        total_withdrawn = Decimal('0.0')
        for field_name in self.warehouse_fields:
            value = cleaned_data.get(field_name)
            if value is not None:
                try:
                    total_withdrawn += Decimal(str(value))
                except DecimalException:
                    raise forms.ValidationError(_(f"أدخل قيمة رقمية صحيحة للمخزن {field_name.split('_')[1]}."))

        total_requested = cleaned_data.get('total_quantity_to_withdraw')
        if isinstance(total_requested, list):
            total_requested = Decimal(str(total_requested[0]))

        if total_withdrawn > total_requested:
            raise forms.ValidationError(_("إجمالي الكمية المسحوبة من المخازن يتجاوز الكمية المطلوبة."))

        return cleaned_data


class AddQuantityToWarehousesForm(forms.Form):
    total_quantity_to_add = forms.DecimalField(
        label=_('إجمالي الكمية المراد إضافتها'),
        min_value=Decimal('0.01'),
        decimal_places=4,  # رفع الخانات العشرية
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly',
            'style': 'width: 150px; background-color: #e3f2fd;',
            'step': '0.0001'  # يسمح بأربع خانات عشرية
        })
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
                    current_quantity = Decimal('0.0000')

                self.fields[f'warehouse_{warehouse.id}'] = forms.DecimalField(
                    label=f"{warehouse.name} ({_('المتاح')}: {current_quantity})",
                    min_value=Decimal('0.00'),
                    decimal_places=4,  # رفع الخانات العشرية
                    required=False,
                    initial=None,
                    widget=forms.NumberInput(attrs={'step': '0.0001'})
                )

    def clean(self):
        cleaned_data = super().clean()
        total_added = Decimal('0.0000')
        for name, value in cleaned_data.items():
            if name.startswith('warehouse_'):
                if value is not None:
                    total_added += Decimal(str(value))

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
