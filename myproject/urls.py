from django.contrib import admin
from django.urls import path, include
from myapp import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('myapp/', include('myapp.urls')),
    path('login/', views.login_view, name='login'),  # إضافة مسار تسجيل الدخول هنا
    path('', views.product_list, name='home'),
]
