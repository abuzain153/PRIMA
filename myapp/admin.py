from django.contrib import admin
from .models import Product, Warehouse, Movement
from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.html import format_html


# إنشاء فورم مخصص للمستخدم عشان نضيف حقل الفريق عند الإنشاء
class CustomUserCreationForm(UserCreationForm):
    team = forms.ModelChoiceField(queryset=Group.objects.all(), required=False, label='الفريق')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'team')

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            if self.cleaned_data['team']:
                user.groups.add(self.cleaned_data['team'])
        return user


# إنشاء فورم مخصص للمستخدم عشان نضيف حقل الفريق عند التعديل
class CustomUserChangeForm(UserChangeForm):
    team = forms.ModelChoiceField(queryset=Group.objects.all(), required=False, label='الفريق')

    class Meta(UserChangeForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'groups', 'user_permissions', 'team')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # قم بتعيين القيمة الأولية لحقل الفريق بناءً على مجموعة المستخدم
            self.fields['team'].initial = self.instance.groups.first()

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            user.groups.clear()  # امسح المجموعات القديمة
            if self.cleaned_data['team']:
                user.groups.add(self.cleaned_data['team'])
        return user


class UserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    list_display = ('id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined', 'get_team')
    list_display_links = ('username',)
    readonly_fields = ('date_joined', 'last_login')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Team', {'fields': ('team',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'password', 'password2', 'team')}
        ),
    )
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions')

    def get_team(self, obj):
        teams = obj.groups.all()
        return ", ".join([team.name for team in teams])
    get_team.short_description = 'الفريق'


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'product_code', 'quantity', 'formatted_quantity', 'unit', 'min_stock', 'team')
    search_fields = ('product_name', 'product_code')
    list_filter = ('unit', 'min_stock', 'team')
    list_editable = ('quantity',)
    actions = ['reset_quantity']

    def formatted_quantity(self, obj):
        if obj.unit == 'יח\'':
            return format_html("{}", int(obj.quantity))
        else:
            return format_html("{}", obj.quantity)
    formatted_quantity.short_description = 'الكمية'
    formatted_quantity.admin_order_field = 'quantity'

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


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    pass
