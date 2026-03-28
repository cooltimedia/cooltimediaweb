"""
Excel Export Service for the Smart Accounting Automation MVP.
Generates a downloadable .xlsx file containing all structured data extracted 
from Panamanian fiscal documents for accounting reconciliation.
"""

from openpyxl import Workbook
from django.http import HttpResponse
from mvp_smart_accounting.models import ParsedDocumentData

class ExcelExportService:
    """
    Service layer responsible for transforming database records 
    into formatted Excel spreadsheets.
    """

    def build_excel_response(self) -> HttpResponse:
        """
        Queries all parsed data and builds an Excel file in memory.
        Returns a Django HttpResponse with the correct MIME type for downloading.
        """
        # 1. Create a new Workbook and select the active sheet
        wb = Workbook()
        ws = wb.active
        ws.title = "Extracted Accounting Data"

        # 2. Define Headers (Panama Specific)
        headers = [
            "ID", "Invoice No.", "CUFE", "Issue Date", 
            "Issuer Name", "Issuer RUC", "Issuer DV",
            "Receiver Name", "Receiver RUC", "Receiver DV",
            "Subtotal ($)", "Tax/ITBMS ($)", "Discount ($)", "Total Paid ($)"
        ]
        ws.append(headers)

        # 3. Fetch data from ParsedDocumentData
        # We use select_related to avoid multiple DB hits for the original filename
        queryset = ParsedDocumentData.objects.all().order_by('-created_at')

        # 4. Populate rows
        for record in queryset:
            ws.append([
                record.id,
                record.document_number,
                record.cufe,
                record.issue_date.strftime("%Y-%m-%d %H:%M") if record.issue_date else "N/A",
                record.issuer_name,
                record.issuer_ruc,
                record.issuer_dv,
                record.receiver_name,
                record.receiver_ruc,
                record.receiver_dv,
                float(record.subtotal),
                float(record.tax_amount),
                float(record.discount),
                float(record.total_paid),
            ])

        # 5. Prepare the HTTP Response
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="smart_accounting_export.xlsx"'
        
        # Save the workbook directly into the response stream
        wb.save(response)
        
        return response