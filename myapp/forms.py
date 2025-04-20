from django import forms
from .models import Product
from django.contrib.auth.forms import PasswordResetForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings # عشان نوصل لإعدادات البريد الإلكتروني

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['product_name', 'product_code', 'quantity', 'unit', 'min_stock']
        widgets = {
            'quantity': forms.NumberInput(attrs={'step': 'any'}),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        try:
            float(quantity)  # التحقق من أن القيمة رقم صالح
        except ValueError:
            raise forms.ValidationError("الكمية يجب أن تكون رقمًا صالحًا.")
        return quantity

    def clean_min_stock(self):
        min_stock = self.cleaned_data['min_stock']
        if min_stock <= 0:
            raise forms.ValidationError("الحد الأدنى يجب أن يكون أكبر من صفر.")
        return min_stock

class ForgetPasswordForm(PasswordResetForm):
    email = forms.EmailField(label='البريد الإلكتروني')

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email=None, html_email_template_name=None):
        subject = render_to_string(subject_template_name, context)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        body = render_to_string(email_template_name, context)
        send_mail(subject, body, from_email, [context['email']])

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(label='البريد الإلكتروني')

    class Meta:
        model = User
        fields = ('username', 'email') # الحقول اللي هتظهر في نموذج التسجيل
