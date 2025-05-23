from django.urls import path
from .views import ProductListView
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('', views.index, name='home'),         # ده هيكون الـ URL الرئيسي واسمه 'home'
    path('index/', views.index, name='index'), # ده هيفضل زي ما هو باسم 'index'
    path('inventory/', views.inventory, name='inventory'),         # صفحة المخزون

    # الروابط الجديدة لخطوتين إضافة المنتج
    path('products/add/', views.add_product_warehouse_selection, name='add_product'),
    path('products/add/details/', views.ProductCreateView.as_view(), name='add_product_details'),

    # الروابط الموجودة بالفعل (تم التعديل في ترتيب إضافة الكمية)
    path('products/', ProductListView.as_view(), name='product_list'),
    path('products/<int:pk>/edit/', views.ProductUpdateView.as_view(), name='edit_product'),
    path('products/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='delete_product'),
    path('products/add_quantity/', views.add_quantity, name='add_quantity'),
    # URL لصفحة توزيع كميات الإضافة على المخازن
    path('products/add_quantity/warehouses/', views.add_quantity, name='add_quantity_warehouses'),
    path('products/withdraw_quantity/', views.withdraw_quantity, name='withdraw_quantity'),
    path('products/low_stock/', views.low_stock_products, name='low_stock_products'),
    path('products/clear/', views.clear_products, name='clear_products'),
    path('products/get_info/<int:product_id>/', views.get_product_info, name='get_product_info'),
    path('reports/', views.show_reports, name='show_reports'),
    path('reports/received/', views.received_report_excel, name='received_report'),
    path('reports/withdrawn/', views.withdrawn_report_excel, name='withdrawn_report'),
    path('reports/search/', views.search_movements, name='search_movements'), # مسار صفحة البحث
    path('reports/search/excel/', views.search_movements_excel, name='search_movements_excel'), # مسار تنزيل البحث كـ Excel
    path('get_products_json/', views.get_products_json, name='get_products_json'), # مسار جلب المنتجات كـ JSON للبحث الذكي
    path('graph/', views.chart_view, name='graph'),
    path('withdrawn-chart/', views.chart_view, name='withdrawn_chart'),
    path('import_excel/', views.import_excel, name='import_excel'),
    path('export_excel/', views.export_excel, name='export_excel'),
    path('import_raw_materials/', views.import_raw_materials, name='import_raw_materials'),
    path('import_maintenance/', views.import_maintenance, name='import_maintenance'),
    # روابط نسيان كلمة المرور وتسجيل المستخدم الجديد
    path('forgot_password/', views.forget_password, name='forgot_password'),
    path('password_reset/confirm/<str:uidb64>/<str:token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('register/', views.register, name='register'),
    path('products/get_products_by_name/', views.get_products_by_name, name='get_products_by_name'),
    path('password_reset/done/', views.password_reset_done, name='password_reset_done'),
    path('products/get_product_by_barcode/', views.get_product_by_barcode, name='get_product_by_barcode'),
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/mark_as_read/<int:notification_id>/', views.mark_as_read, name='mark_notification_as_read'), # <--- السطر اللي ضفته
    path('products/details/<int:product_id>/', views.view_product_details, name='view_product_details'),
]
