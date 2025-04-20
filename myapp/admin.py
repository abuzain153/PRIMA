from django.contrib import admin
from .models import Product, Movement

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'product_code', 'quantity', 'unit', 'min_stock')
    search_fields = ('product_name', 'product_code')
    list_filter = ('unit', 'min_stock')
    list_editable = ('quantity',)
    actions = ['reset_quantity']

    def reset_quantity(self, request, queryset):
        queryset.update(quantity=0)
        self.message_user(request, "تم إعادة تعيين الكمية إلى 0.")
    reset_quantity.short_description = "إعادة تعيين الكمية"

@admin.register(Movement)
class MovementAdmin(admin.ModelAdmin):
    list_display = ('product', 'movement_type', 'quantity', 'date')
    list_filter = ('movement_type', 'date')
    autocomplete_fields = ('product',)
    readonly_fields = ('date',)
