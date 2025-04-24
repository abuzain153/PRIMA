from django import forms
from .models import Product
from django.contrib.auth.forms import PasswordResetForm, UserCreationForm
from django.contrib.auth.models import User, Group
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class ProductForm(forms.ModelForm):
    product_name = forms.CharField(label=_('اسم المنتج'))
    product_code = forms.CharField(label=_('رمز المنتج'))
    quantity = forms.FloatField(label=_('الكمية'), widget=forms.NumberInput(attrs={'step': 'any'}))
    unit = forms.CharField(label=_('الوحدة'))
    min_stock = forms.IntegerField(label=_('الحد الأدنى'))

    class Meta:
        model = Product
        fields = ['product_name', 'product_code', 'quantity', 'unit', 'min_stock']
        widgets = {
            'quantity': forms.NumberInput(attrs={'step': 'any'}),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        try:
            float(quantity)
        except ValueError:
            raise forms.ValidationError(_("الكمية يجب أن تكون رقمًا صالحًا."))
        return quantity

    def clean_min_stock(self):
        min_stock = self.cleaned_data['min_stock']
        if min_stock <= 0:
            raise forms.ValidationError(_("الحد الأدنى يجب أن يكون أكبر من صفر."))
        return min_stock

    def clean_product_code(self):
        product_code = self.cleaned_data['product_code']
        if self.instance:  # لو الفورم ده لتعديل منتج موجود
            if Product.objects.filter(product_code=product_code).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError(_("رمز المنتج موجود بالفعل."))
        else:  # لو الفورم ده لإضافة منتج جديد
            if Product.objects.filter(product_code=product_code).exists():
                raise forms.ValidationError(_("رمز المنتج موجود بالفعل."))
        return product_code

class ForgetPasswordForm(PasswordResetForm):
    email = forms.EmailField(label=_('البريد الإلكتروني'))

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email=None, html_email_template_name=None):
        subject = render_to_string(subject_template_name, context)
        subject = ''.join(subject.splitlines())
        body = render_to_string(email_template_name, context)
        html_body = render_to_string(html_email_template_name, context) if html_email_template_name else None
        send_mail(subject, body, from_email, [context['email']], html_message=html_body)

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(label=_('البريد الإلكتروني'))
    team = forms.ModelChoiceField(queryset=Group.objects.all(), empty_label=_("اختر فريقك"), label=_("الفريق"))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email', 'team')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        team = self.cleaned_data['team']
        if commit:
            user.save()
            user.groups.add(team)
        return user
