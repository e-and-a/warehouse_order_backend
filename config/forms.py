from django import forms
from django.contrib.auth.forms import AuthenticationForm

from apps.catalog.models import Product
from apps.orders.models import Customer


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )


class ProductCreateForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "sku", "description", "price", "category", "is_active"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class OrderCreateForm(forms.Form):
    customer = forms.ModelChoiceField(queryset=Customer.objects.all())
    product = forms.ModelChoiceField(queryset=Product.objects.filter(is_active=True))
    quantity = forms.IntegerField(min_value=1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customer"].queryset = Customer.objects.order_by("name")
        self.fields["product"].queryset = Product.objects.filter(is_active=True).order_by("name")
