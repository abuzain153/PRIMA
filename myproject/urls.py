from django.contrib import admin
from django.urls import path, include
from myapp import views
from django.conf import settings
from django.conf.urls.static import static
import os

urlpatterns = [
    path('admin/', admin.site.urls),
    path('myapp/', include('myapp.urls')),
    path('login/', views.login_view, name='login'),  # إضافة مسار تسجيل الدخول هنا
    path('', include('myapp.urls')), # عشان الـ URL الرئيسي يروح على urls بتاع myapp
] + static(settings.STATIC_URL, document_root=os.path.join(settings.BASE_DIR, 'myapp/static'))
