from django.contrib import admin
from .models import Product, Movement
from django.contrib.auth.models import Group

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'product_code', 'quantity', 'unit', 'min_stock', 'team')
    search_fields = ('product_name', 'product_code')
    list_filter = ('unit', 'min_stock', 'team')
    list_editable = ('quantity',)
    actions = ['reset_quantity']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        if request.user.groups.exists():
            user_group = request.user.groups.first()
            if user_group and user_group.name == "فريق المواد الخام":
                return qs.filter(team=user_group)

            elif user_group and user_group.name == "فريق الصيانة":
                return qs.filter(team=user_group)

        return qs.none()

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
