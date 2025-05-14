from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from django.db.models import Sum

class Warehouse(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_('اسم المخزن'))

    def __str__(self):
        return self.name

class Product(models.Model):
    product_name = models.CharField(max_length=255, verbose_name=_('اسم المنتج'))
    product_code = models.CharField(max_length=50, unique=True, verbose_name=_('رمز المنتج'))
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name=_('الكمية الكلية'))
    unit = models.CharField(max_length=50, verbose_name=_('الوحدة'))
    min_stock = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_('الحد الأدنى للمخزون'))
    team = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='products', null=True, blank=True, verbose_name=_('الفريق'))
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products_added_by', verbose_name=_('المستخدم'))
    warehouses = models.ManyToManyField(Warehouse, through='ProductWarehouse', related_name='products', verbose_name=_('المخازن'))
    formatted_quantity_display = models.CharField(max_length=50, blank=True, null=True)
    formatted_min_stock_display = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.product_name

    def _format_decimal(self, value):
        decimal_value = Decimal(str(value)).quantize(Decimal('0.00'))
        if decimal_value == decimal_value.to_integral_value():
            return str(decimal_value.to_integral_value())
        else:
            return format(decimal_value, '.2f')

    def save(self, *args, **kwargs):
        self.formatted_quantity_display = self._format_decimal(self.quantity)
        self.formatted_min_stock_display = self._format_decimal(self.min_stock)
        super().save(*args, **kwargs)

class ProductWarehouse(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name=_('المنتج'))
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, verbose_name=_('المخزن'))
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        unique_together = ('product', 'warehouse')

    def __str__(self):
        return f"{self.product.product_name} في {self.warehouse.name}: {self.quantity}"

class Movement(models.Model):
    MOVEMENT_TYPES = (
        ('استلام', 'استلام'),
        ('سحب', 'سحب'),
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name=_('المنتج'))
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('المخزن'))
    movement_type = models.CharField(max_length=50, choices=MOVEMENT_TYPES, verbose_name=_('نوع الحركة'))
    quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_('الكمية'))
    date = models.DateTimeField(auto_now_add=True, verbose_name=_('التاريخ'))
    quantity_after = models.FloatField(null=True, blank=True, verbose_name=_('الكمية بعد الحركة'))
    stock_after_movement = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_('الكمية بالمخزون بعد الحركة'))
    team = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='movements', null=True, blank=True, verbose_name=_('الفريق'))
    current_stock_at_movement = models.IntegerField(null=True, blank=True, verbose_name=_("الرصيد الحالي بالمخزن وقت الحركة"))
    total_stock_at_movement = models.IntegerField(null=True, blank=True, verbose_name=_("الرصيد الكلي وقت الحركة"))

    def __str__(self):
        return f"{self.product.product_name} - {self.movement_type} - {self.quantity} في {self.warehouse}"

    def save(self, *args, **kwargs):
        if self.movement_type == "سحب" and self.quantity > (self.product.productwarehouse_set.filter(warehouse=self.warehouse).first().quantity if self.warehouse else 0):
            raise ValueError("الكمية المسحوبة أكبر من المخزون المتوفر في هذا المخزن.")

        # تسجيل لقطة من أرصدة المخزون فقط عند إنشاء حركة جديدة
        if not self.pk:
            if self.warehouse:
                product_warehouse = ProductWarehouse.objects.filter(product=self.product, warehouse=self.warehouse).first()
                self.current_stock_at_movement = int(product_warehouse.quantity) if product_warehouse else 0
            else:
                self.current_stock_at_movement = 0

            total_stock = ProductWarehouse.objects.filter(product=self.product).aggregate(Sum('quantity'))['quantity__sum'] or 0
            self.total_stock_at_movement = int(total_stock)

        super().save(*args, **kwargs)

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('المستخدم'))
    notification_type = models.CharField(
        max_length=20,
        choices=[
            ('low_stock', 'Low Stock'),
            ('new_product', 'New Product'),
            ('quantity_added', 'Quantity Added'),
            ('quantity_withdrawn', 'Quantity Withdrawn'),
        ],
        verbose_name=_('نوع الإشعار')
    )
    message = models.TextField(verbose_name=_('الرسالة'))
    is_read = models.BooleanField(default=False, verbose_name=_('مقروء'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاريخ الإنشاء'))
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('المنتج'))

    def __str__(self):
        return f"إشعار لـ {self.user.username}: {self.get_notification_type_display()}"

    def get_notification_type_display(self):
        return dict(self.NOTIFICATION_TYPE_CHOICES).get(self.notification_type, self.notification_type)

    NOTIFICATION_TYPE_CHOICES = [
        ('low_stock', 'Low Stock'),
        ('new_product', 'New Product'),
        ('quantity_added', 'Quantity Added'),
        ('quantity_withdrawn', 'Quantity Withdrawn'),
    ]
