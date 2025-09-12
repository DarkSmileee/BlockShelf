from django import forms
from .models import InventoryItem
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm as DjangoPasswordChangeForm
from .models import AppConfig

User = get_user_model()

class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = ['name', 'part_id', 'color', 'quantity_total', 'quantity_used', 'storage_location', 'image_url', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned = super().clean()
        qt = cleaned.get('quantity_total') or 0
        qu = cleaned.get('quantity_used') or 0
        if qu > qt:
            self.add_error('quantity_used', 'Used quantity cannot exceed total quantity.')
        return cleaned

class ImportCSVForm(forms.Form):
    file = forms.FileField(
        label="Inventory file (CSV/XLS/XLSX)",
        help_text=("Upload a CSV or Excel file with header: "
                   "name,part_id,color,quantity_total,quantity_used,storage_location,image_url,notes"),
        widget=forms.ClearableFileInput(
            attrs={
                "accept": (
                    ".csv,"
                    "text/csv,"
                    "application/vnd.ms-excel,"  # .xls
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"  # .xlsx
                ),
                "class": "form-control",
            }
        ),
    )

class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email"]  # email is optional in your settings
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control", "autocomplete": "username"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "autocomplete": "email"}),
        }


class PasswordChangeForm(DjangoPasswordChangeForm):
    """
    Just adds Bootstrap-ish classes. Uses Django's built-in validation.
    """
    old_password = forms.CharField(
        label="Current password",
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "current-password"}),
    )
    new_password1 = forms.CharField(
        label="New password",
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )
    new_password2 = forms.CharField(
        label="New password (again)",
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )
    
class InviteCollaboratorForm(forms.Form):
    email = forms.EmailField(label="Invitee email")
    can_edit = forms.BooleanField(
        label="Allow editing (add/update items)", required=False, initial=True
    )
    can_delete = forms.BooleanField(
        label="Allow deleting items", required=False, initial=False
    )
    
class InventoryImportForm(forms.Form):
    STRATEGY_CHOICES = [
        ("append", "Append new rows"),
        ("update", "Update existing by Part ID"),
        ("replace", "Replace my inventory"),
    ]
    DELIMITER_CHOICES = [
        (",", "Comma (,)"),
        (";", "Semicolon (;)"),
        ("\t", "Tab"),
    ]

    file = forms.FileField(label="CSV file")
    strategy = forms.ChoiceField(choices=STRATEGY_CHOICES, initial="append")
    delimiter = forms.ChoiceField(choices=DELIMITER_CHOICES, initial=",")
    has_header = forms.BooleanField(
        label="File includes header row", required=False, initial=True
    )

    def clean_file(self):
        f = self.cleaned_data["file"]
        # Light validation so users can also upload .txt exports
        name = (f.name or "").lower()
        if not (name.endswith(".csv") or name.endswith(".txt")):
            raise forms.ValidationError("Please upload a .csv or .txt file.")
        return f


class InviteCollaboratorForm(forms.Form):
    email = forms.EmailField(label="Invitee email")
    can_edit = forms.BooleanField(
        label="Allow editing (add/update items)", required=False, initial=True
    )
    can_delete = forms.BooleanField(
        label="Allow deleting items", required=False, initial=False
    )
    
class AppConfigForm(forms.ModelForm):
    class Meta:
        model = AppConfig
        fields = [
            "site_name",
            "items_per_page",
            "allow_registration",
            "rebrickable_api_key",
            "default_from_email",
        ]
        widgets = {
            "site_name": forms.TextInput(attrs={"class": "form-control"}),
            "items_per_page": forms.NumberInput(attrs={"class": "form-control", "min": 5, "max": 500, "step": 1}),
            "allow_registration": forms.CheckboxInput(),
            "rebrickable_api_key": forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
            "default_from_email": forms.EmailInput(attrs={"class": "form-control"}),
        }