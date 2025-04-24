from django.contrib import admin
from django.urls import path, include
from myapp import views # استيراد views من myapp عشان لو login_view هناك
from django.conf.urls.i18n import set_language # **[أضف هذا السطر]**

urlpatterns = [
    path('admin/', admin.site.urls),
    path('myapp/', include('myapp.urls')),
    path('login/', views.login_view, name='login'),    # لو login_view في myapp/views.py
    path('', include('myapp.urls')), # الـ URL الرئيسي هيشمل URLs تطبيق myapp
    path('i18n/setlang/', set_language, name='set_language'), # **[أضف هذا السطر]**
]
