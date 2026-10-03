"""Forms used by the FraagranSoul storefront and staff dashboard."""

import re

from django import forms
from django.utils.text import slugify

from .models import Category, Order, Product, ProductVariant


def unique_slug(model, text, instance=None):
    """Return a slug for `text` that no other row of `model` is using."""
    base = slugify(text)[:45] or "item"
    slug = base
    number = 2
    others = model.objects.exclude(pk=instance.pk) if instance and instance.pk else model.objects.all()
    while others.filter(slug=slug).exists():
        slug = f"{base}-{number}"
        number += 1
    return slug


class CheckoutForm(forms.ModelForm):
    """Delivery details collected on the checkout page."""

    class Meta:
        model = Order
        fields = ["full_name", "email", "phone", "address", "city", "pin_code"]

    def clean_phone(self):
        """Accept a 10-digit Indian mobile number, with or without +91."""
        digits = re.sub(r"\D", "", self.cleaned_data["phone"])
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        elif len(digits) == 11 and digits.startswith("0"):
            digits = digits[1:]

        if not re.fullmatch(r"[6-9]\d{9}", digits):
            raise forms.ValidationError("Enter a valid 10-digit mobile number.")
        return digits

    def clean_pin_code(self):
        """Indian PIN codes are six digits and never start with zero."""
        pin_code = self.cleaned_data["pin_code"].strip()
        if not re.fullmatch(r"[1-9]\d{5}", pin_code):
            raise forms.ValidationError("Enter a valid 6-digit PIN code.")
        return pin_code


class ProductForm(forms.ModelForm):
    """Perfume details edited from the staff dashboard."""

    class Meta:
        model = Product
        fields = ["name", "brand", "gender", "category", "description", "notes", "image", "is_featured", "is_new"]
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}
        labels = {
            "is_featured": "Feature on the home page",
            "is_new": "Show the NEW badge",
        }

    def save(self, commit=True):
        """Create the URL slug from the name the first time a perfume is saved."""
        product = super().save(commit=False)
        if not product.slug:
            product.slug = unique_slug(Product, product.name, product)
        if commit:
            product.save()
        return product


VariantFormSet = forms.inlineformset_factory(
    Product,
    ProductVariant,
    fields=["volume_ml", "price", "old_price", "stock"],
    extra=1,
    min_num=1,
    validate_min=True,
    can_delete=True,
)


class CategoryForm(forms.ModelForm):
    """A fragrance family added from the staff dashboard."""

    class Meta:
        model = Category
        fields = ["name"]

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if Category.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError("This family already exists.")
        return name

    def save(self, commit=True):
        category = super().save(commit=False)
        category.slug = unique_slug(Category, category.name, category)
        if commit:
            category.save()
        return category
