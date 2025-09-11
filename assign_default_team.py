import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "inventory_management.settings")  # عدّل الاسم حسب مشروعك
django.setup()

from django.contrib.auth.models import User, Group

default_team = Group.objects.filter(name="فريق المواد الخام").first()

if not default_team:
    print("لم يتم العثور على الفريق الافتراضي. أنشئه أولاً في الـ Admin.")
else:
    users_without_team = User.objects.filter(groups__isnull=True)
    for user in users_without_team:
        user.groups.add(default_team)
        user.save()
        print(f"تم ربط {user.username} بالفريق الافتراضي.")

    print("تم الانتهاء من ربط جميع المستخدمين بالفريق الافتراضي.")
