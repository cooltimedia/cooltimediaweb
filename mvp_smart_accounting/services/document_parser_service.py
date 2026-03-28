"""
Document Parser Service for the Smart Accounting Automation MVP.
Orchestrates the workflow for Panamanian Fiscal Documents, 
mapping Issuer, Receiver, and Financial data to the database.
"""

from mvp_smart_accounting.models import (
    DocumentProcessingLog,
    DocumentProcessingStatus,
    ParsedDocumentData,
)


class DocumentParserService:
    """
    Coordinator service that manages the end-to-end processing of a document.
    Updated to handle complex Panamanian invoice structures.
    """

    def process_document(self, uploaded_document):
        """
        Main entry point for document processing.
        Transitions the document through its lifecycle and persists extracted data.
        """
        # 1. Start Processing Phase
        uploaded_document.processing_status = DocumentProcessingStatus.PROCESSING
        uploaded_document.save(update_fields=["processing_status"])

        self._create_log(
            uploaded_document=uploaded_document,
            step_name="document_processing_started",
            status="success",
            message="Document processing started.",
        )

        try:
            # 2. Extract raw text from physical file (PDF)
            extracted_text = self._extract_text_from_pdf(uploaded_document)
            
            # 3. Parse text into structured Panamanian fiscal fields
            parsed_fields = self._extract_structured_fields(extracted_text)

            # 4. Persist data into the updated ParsedDocumentData model
            ParsedDocumentData.objects.update_or_create(
                uploaded_document=uploaded_document,
                defaults={
                    # Header Info
                    "document_number": parsed_fields.get("document_number", ""),
                    "cufe": parsed_fields.get("cufe", ""),
                    "issue_date": parsed_fields.get("issue_date"),
                    
                    # Issuer
                    "issuer_name": parsed_fields.get("issuer_name", ""),
                    "issuer_ruc": parsed_fields.get("issuer_ruc", ""),
                    "issuer_dv": parsed_fields.get("issuer_dv", ""),
                    
                    # Receiver
                    "receiver_name": parsed_fields.get("receiver_name", ""),
                    "receiver_type": parsed_fields.get("receiver_type", ""),
                    "receiver_ruc": parsed_fields.get("receiver_ruc", ""),
                    "receiver_dv": parsed_fields.get("receiver_dv", ""),
                    
                    # Financial Totals
                    "subtotal": parsed_fields.get("subtotal", 0.00),
                    "tax_amount": parsed_fields.get("tax_amount", 0.00),
                    "discount": parsed_fields.get("discount", 0.00),
                    "total_paid": parsed_fields.get("total_paid", 0.00),
                    
                    # Metadata
                    "raw_extracted_text": extracted_text,
                    "extraction_confidence": parsed_fields.get("extraction_confidence"),
                },
            )

            # 5. Success Finalization
            uploaded_document.processing_status = DocumentProcessingStatus.PROCESSED
            uploaded_document.save(update_fields=["processing_status"])

            self._create_log(
                uploaded_document=uploaded_document,
                step_name="document_processing_completed",
                status="success",
                message="Document processing completed successfully.",
            )

        except Exception as e:
            # Error Handling: Ensure we log the failure and update status
            uploaded_document.processing_status = DocumentProcessingStatus.FAILED
            uploaded_document.save(update_fields=["processing_status"])
            
            self._create_log(
                uploaded_document=uploaded_document,
                step_name="document_processing_error",
                status="failed",
                message=f"An error occurred: {str(e)}",
            )

    def _extract_text_from_pdf(self, uploaded_document):
        """Helper to call the PDF extraction engine."""
        from .pdf_text_extraction_service import PdfTextExtractionService
        return PdfTextExtractionService().extract_text(
            file_path=uploaded_document.original_file.path
        )

    def _extract_structured_fields(self, extracted_text):
        """Helper to call the Panama-specific extraction logic (Regex/AI)."""
        from .tax_information_extraction_service import TaxInformationExtractionService
        return TaxInformationExtractionService().extract_fields(
            extracted_text=extracted_text
        )

    def _create_log(self, uploaded_document, step_name, status, message):
        """Utility method to record the process audit trail."""
        DocumentProcessingLog.objects.create(
            uploaded_document=uploaded_document,
            step_name=step_name,
            status=status,
            message=message,
        )