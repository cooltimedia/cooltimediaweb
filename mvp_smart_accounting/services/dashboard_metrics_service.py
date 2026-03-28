"""
Dashboard Metrics Service for the Smart Accounting Automation MVP.
Calculates financial aggregations and document processing statistics 
to power the interactive charts in the user dashboard.
"""

from django.db.models import Sum, Count
from mvp_smart_accounting.models import UploadedDocument, ParsedDocumentData, DocumentProcessingStatus

class DashboardMetricsService:
    """
    Service layer responsible for aggregating database records into 
    meaningful metrics for business intelligence and data visualization.
    """

    def build_summary(self) -> dict:
        """
        Gathers all key indicators for the main dashboard view.
        Returns a dictionary containing counts, totals, and chart data.
        """
        return {
            "total_documents_processed": self._get_total_processed_count(),
            "financial_overview": self._get_financial_totals(),
            "top_issuers": self._get_top_issuers(),
            "status_distribution": self._get_status_distribution(),
        }

    def _get_total_processed_count(self) -> int:
        """Returns the count of documents successfully processed."""
        return UploadedDocument.objects.filter(
            processing_status=DocumentProcessingStatus.PROCESSED
        ).count()

    def _get_financial_totals(self) -> dict:
        """
        Aggregates Subtotal, Tax (ITBMS), and Total Paid from all 
        parsed documents in the system.
        """
        totals = ParsedDocumentData.objects.aggregate(
            sum_subtotal=Sum('subtotal'),
            sum_tax=Sum('tax_amount'),
            sum_total=Sum('total_paid')
        )
        
        # Ensure we return 0.00 if no data exists
        return {
            "subtotal": float(totals['sum_subtotal'] or 0.00),
            "itbms": float(totals['sum_tax'] or 0.00),
            "total": float(totals['sum_total'] or 0.00),
        }

    def _get_top_issuers(self) -> list:
        """
        Identifies the top 5 companies (Emisores) by total amount spent.
        Ideal for a 'Top Suppliers' Bar Chart.
        """
        top_issuers = ParsedDocumentData.objects.values('issuer_name').annotate(total=Sum('total_paid')).order_by('-total')[:5]

        return [
                {
                    'issuer_name': item['issuer_name'], 
                    'total': float(item['total']) 
                } for item in top_issuers
            ]

    def _get_status_distribution(self) -> dict:
        """
        Counts documents by their current processing status.
        Ideal for a Doughnut/Pie Chart showing system health.
        """
        distribution = UploadedDocument.objects.values('processing_status').annotate(
            count=Count('id')
        )
        
        # Transform into a simple key-value pair for easy template access
        return {item['processing_status']: item['count'] for item in distribution}