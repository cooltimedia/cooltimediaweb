"""
Models for the Smart Accounting Automation MVP.
Updated to support Panamanian Fiscal requirements including CUFE, 
separate Issuer/Receiver data, and tax breakdowns.
Author: Cooltimedia
Date: March 28, 2026
"""

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

# --- Choices ---

class DocumentProcessingStatus(models.TextChoices):
    """Lifecycle stages of a document."""
    UPLOADED = "uploaded", "Uploaded"
    PROCESSING = "processing", "Processing"
    PROCESSED = "processed", "Processed"
    FAILED = "failed", "Failed"

class DocumentType(models.TextChoices):
    """Types of Panamanian fiscal documents."""
    INVOICE = "invoice", "Factura Electrónica"
    RECEIPT = "receipt", "Comprobante"
    TAX_DOCUMENT = "tax_document", "Documento Fiscal"
    UNKNOWN = "unknown", "Unknown"

# --- Models ---

class UploadedDocument(models.Model):
    """Represents the physical file uploaded for processing."""
    original_file = models.FileField(
        verbose_name="Original File",
        upload_to="smart_accounting/uploaded_documents/%Y/%m/%d/",
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "xlsx", "xls"])],
    )
    original_file_name = models.CharField(max_length=255, verbose_name="File Name")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_documents",
    )
    processing_status = models.CharField(
        max_length=20,
        choices=DocumentProcessingStatus.choices,
        default=DocumentProcessingStatus.UPLOADED,
    )
    document_type = models.CharField(
        max_length=30,
        choices=DocumentType.choices,
        default=DocumentType.UNKNOWN,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Uploaded Document"

    def __str__(self) -> str:
        return f"{self.original_file_name} ({self.processing_status})"


class ParsedDocumentData(models.Model):
    """
    Stores extracted data from Panamanian Fiscal Documents.
    Differentiates between Issuer (Emisor) and Receiver (Receptor).
    """
    uploaded_document = models.OneToOneField(
        UploadedDocument,
        on_delete=models.CASCADE,
        related_name="parsed_data",
    )

    # --- Header & General Info ---
    document_number = models.CharField(max_length=100, blank=True, verbose_name="No. Factura")
    cufe = models.CharField(max_length=100, blank=True, verbose_name="CUFE")
    issue_date = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Emisión")

    # --- Issuer Data (Emisor) ---
    issuer_name = models.CharField(max_length=255, blank=True, verbose_name="Nombre Emisor")
    issuer_ruc = models.CharField(max_length=255, blank=True, verbose_name="RUC Emisor")
    issuer_dv = models.CharField(max_length=50, blank=True, verbose_name="DV Emisor")

    # --- Receiver Data (Receptor) ---
    receiver_name = models.CharField(max_length=255, blank=True, verbose_name="Nombre Receptor")
    receiver_type = models.CharField(max_length=100, blank=True, verbose_name="Tipo de Receptor")
    receiver_ruc = models.CharField(max_length=255, blank=True, verbose_name="RUC Receptor")
    receiver_dv = models.CharField(max_length=50, blank=True, verbose_name="DV Receptor")
    

    # --- Financial Totals (Panama Standard) ---
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="ITBMS / Impuesto")
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    # --- Metadata ---
    raw_extracted_text = models.TextField(blank=True)
    extraction_confidence = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Parsed Document Data"

    def __str__(self) -> str:
        return f"Data for {self.document_number} - {self.issuer_name}"


class DocumentProcessingLog(models.Model):
    """Technical audit trail for the parsing process."""
    uploaded_document = models.ForeignKey(
        UploadedDocument,
        on_delete=models.CASCADE,
        related_name="processing_logs",
    )
    step_name = models.CharField(max_length=100)
    status = models.CharField(max_length=30)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]