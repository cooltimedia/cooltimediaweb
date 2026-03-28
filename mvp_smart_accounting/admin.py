"""
Admin configuration for the Smart Accounting Automation MVP.
Registers models to the Django Admin and customizes the list displays
for better document tracking and auditing.
"""

from django.contrib import admin
from .models import UploadedDocument, ParsedDocumentData, DocumentProcessingLog

@admin.register(UploadedDocument)
class UploadedDocumentAdmin(admin.ModelAdmin):
    """
    Admin view for uploaded files. Includes filters by status 
    and uploader for quick management.
    """
    list_display = ("original_file_name", "uploaded_by", "processing_status", "document_type", "uploaded_at")
    list_filter = ("processing_status", "document_type", "uploaded_at")
    search_fields = ("original_file_name", "uploaded_by__username")
    readonly_fields = ("uploaded_at",)
    ordering = ("-uploaded_at",)

@admin.register(ParsedDocumentData)
class ParsedDocumentDataAdmin(admin.ModelAdmin):
    """
    Admin view for extracted data. Focuses on Panama-specific fields 
    like RUC, CUFE, and financial totals.
    """
    list_display = ("document_number", "issuer_name", "issuer_ruc", "total_paid", "extraction_confidence", "created_at")
    list_filter = ("extraction_confidence", "created_at")
    search_fields = ("document_number", "cufe", "issuer_name", "issuer_ruc", "receiver_name")
    readonly_fields = ("created_at", "updated_at")

@admin.register(DocumentProcessingLog)
class DocumentProcessingLogAdmin(admin.ModelAdmin):
    """
    Technical audit log view. Essential for debugging failed 
    extractions during the demo.
    """
    list_display = ("uploaded_document", "step_name", "status", "created_at")
    list_filter = ("status", "step_name")
    readonly_fields = ("created_at",)