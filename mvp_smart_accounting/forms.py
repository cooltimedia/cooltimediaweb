"""
Forms for the Smart Accounting Automation MVP.
Handles user authentication and document upload validation, 
including file type and size restrictions.
"""

from django import forms
from .models import UploadedDocument

class LoginForm(forms.Form):
    """
    Standard login form for user authentication.
    Includes accessibility (tabindex) and autocomplete attributes 
    to improve UX and password manager compatibility.
    """
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'placeholder': 'Username', 
            'class': 'form-control',
            'tabindex': '1',
            'autocomplete': 'username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Password', 
            'class': 'form-control',
            'tabindex': '2',
            'autocomplete': 'current-password'
        })
    )


class UploadedDocumentForm(forms.ModelForm):
    """
    Form for handling single document uploads (PDF/Excel).
    Includes validation for file size to ensure system stability.
    """
    class Meta:
        model = UploadedDocument
        fields = ["original_file"]
        widgets = {
            'original_file': forms.FileInput(attrs={
                'class': 'file-upload-input',
                'tabindex': '3'  # Logical continuation of the flow
            }),
        }

    def clean_original_file(self):
        """
        Custom validation to restrict file size.
        Current limit: 10 MB.
        """
        uploaded_file = self.cleaned_data.get("original_file")

        if uploaded_file:
            # Check if the file size exceeds 10 Megabytes (10 * 1024 * 1024 bytes)
            if uploaded_file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("The uploaded file cannot exceed 10 MB.")
        
        return uploaded_file