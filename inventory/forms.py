from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm as DjangoPasswordChangeForm

from .models import (
    InventoryItem,
    AppConfig,
    UserPreference,
    Note,
)

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
                   "name,part_id,color,quantity_total,quantity_used,storage_location,image_url,notes. "
                   "Max file size: 10MB"),
        widget=forms.ClearableFileInput(
            attrs={
                "accept": (
                    ".csv,"
                    "text/csv,"
                    "application/vnd.ms-excel,"
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ),
                "class": "form-control",
            }
        ),
    )

    def clean_file(self):
        from django.conf import settings
        file = self.cleaned_data.get('file')
        if file:
            # Check file size
            max_size = getattr(settings, 'FILE_UPLOAD_MAX_MEMORY_SIZE', 10 * 1024 * 1024)
            if file.size > max_size:
                raise forms.ValidationError(
                    f"File size exceeds maximum allowed size of {max_size // (1024*1024)}MB."
                )

            # Validate file extension
            allowed_extensions = ['.csv', '.xls', '.xlsx']
            file_name = file.name.lower()
            if not any(file_name.endswith(ext) for ext in allowed_extensions):
                raise forms.ValidationError(
                    "Invalid file type. Only CSV, XLS, and XLSX files are allowed."
                )
        return file


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control", "autocomplete": "username"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "autocomplete": "email"}),
        }
        help_texts = {
            "username": None,
        }


class PasswordChangeForm(DjangoPasswordChangeForm):
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
        name = (f.name or "").lower()
        if not (name.endswith(".csv") or name.endswith(".txt")):
            raise forms.ValidationError("Please upload a .csv or .txt file.")
        return f


# ---------- NEW SPLIT FOR SETTINGS ----------

class AppConfigForm(forms.ModelForm):
    """Admin-only site settings."""
    class Meta:
        model = AppConfig
        fields = [
            "site_name",
            "allow_registration",
            "default_from_email",
        ]
        widgets = {
            "site_name": forms.TextInput(attrs={"class": "form-control"}),
            "allow_registration": forms.CheckboxInput(),
            "default_from_email": forms.EmailInput(attrs={"class": "form-control"}),
        }


class UserSettingsForm(forms.ModelForm):
    """Per-user settings visible to all authenticated users."""
    class Meta:
        model = UserPreference
        fields = ["items_per_page", "rebrickable_api_key"]
        widgets = {
            "items_per_page": forms.NumberInput(attrs={"class": "form-control", "min": 5, "max": 500, "step": 1}),
            "rebrickable_api_key": forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
        }


class NoteForm(forms.ModelForm):
    """Form for creating and editing user notes."""
    class Meta:
        model = Note
        fields = ["title", "description"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Note title"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 10, "placeholder": "Write your note here..."}),
        }
