from .models import Notification

def user_notifications(request):
    if request.user.is_authenticated:
        notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')[:5]  # عرض آخر 5 إشعارات غير مقروءة كمثال
        return {'user_notifications': notifications}
    return {}
