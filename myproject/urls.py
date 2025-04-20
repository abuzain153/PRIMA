from django.contrib import admin
from django.urls import path, include
from myapp import views # استيراد views من myapp عشان لو login_view هناك

urlpatterns = [
    path('admin/', admin.site.urls),
    path('myapp/', include('myapp.urls')),
    path('login/', views.login_view, name='login'),   # لو login_view في myapp/views.py
    path('', include('myapp.urls')), # الـ URL الرئيسي هيشمل URLs تطبيق myapp
]
