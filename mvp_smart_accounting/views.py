"""
Views for the Smart Accounting Automation MVP.
Handles authentication, document processing triggers, dashboard metrics, 
and data exportation for Cooltimedia's solution demo.
"""

from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_sameorigin

# Local imports
from .forms import LoginForm, UploadedDocumentForm
from .models import UploadedDocument
from .services.dashboard_metrics_service import DashboardMetricsService
from .services.document_parser_service import DocumentParserService
from .services.excel_export_service import ExcelExportService


class LoginView(FormView):
    """
    Handles user authentication for the Smart Accounting platform.
    Validates credentials and establishes a session for the user.
    """
    template_name = "mvp_smart_accounting/login.html"
    form_class = LoginForm

    def form_valid(self, form):
        """
        Authenticates the user against the database and redirects to the dashboard
        upon successful login.
        """
        user = authenticate(
            self.request,
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password"],
        )

        if user is None:
            form.add_error(None, "Invalid username or password.")
            return self.form_invalid(form)

        login(self.request, user)
    
        # --- DYNAMIC REDIRECTION LOGIC ---
        # 1. Check if there is a 'next' parameter in the URL (standard Django)
        next_url = self.request.GET.get('next')
        if next_url:
            return redirect(next_url)

        # 2. Default fallback for THIS specific demo
        return redirect("mvp_smart_accounting:dashboard")    


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Renders the main dashboard interface.
    Aggregates financial and processing metrics via DashboardMetricsService.
    """
    template_name = "mvp_smart_accounting/dashboard.html"

    def get_context_data(self, **kwargs):
        """
        Injects the summary metrics (counts, amounts, charts data) into the template.
        """
        context = super().get_context_data(**kwargs)
        # Using the service layer to keep the view clean
        context["dashboard_summary"] = DashboardMetricsService().build_summary()
        return context


class UploadedDocumentCreateView(LoginRequiredMixin, FormView):
    """
    Handles the upload of new PDF/Excel documents.
    Triggers the automated parsing process immediately after a successful upload.
    """
    template_name = "mvp_smart_accounting/upload_document.html"
    form_class = UploadedDocumentForm

    def form_valid(self, form):
        """
        Saves the file, records metadata (filename, uploader), and 
        calls the DocumentParserService to start extraction.
        """
        uploaded_document = form.save(commit=False)
        # Store original filename before it gets potentially renamed by Django's storage
        uploaded_document.original_file_name = uploaded_document.original_file.name
        uploaded_document.uploaded_by = self.request.user
        uploaded_document.save()

        # Trigger the AI/Regex parsing logic
        DocumentParserService().process_document(uploaded_document=uploaded_document)

        return redirect(
            "mvp_smart_accounting:document_detail",
            pk=uploaded_document.pk,
        )


class UploadedDocumentListView(LoginRequiredMixin, ListView):
    """
    Displays a paginated list of all documents uploaded by the organization.
    Useful for tracking processing status and history.
    """
    template_name = "mvp_smart_accounting/document_list.html"
    model = UploadedDocument
    context_object_name = "documents"
    paginate_by = 20


@method_decorator(xframe_options_sameorigin, name='dispatch')
class UploadedDocumentDetailView(LoginRequiredMixin, DetailView):
    """
    Provides a detailed view of a single document, showing the original file 
    link alongside the structured data extracted by the AI.
    """
    template_name = "mvp_smart_accounting/document_detail.html"
    model = UploadedDocument
    context_object_name = "document"


class ExportParsedDocumentsExcelView(LoginRequiredMixin, View):
    """
    Generates and returns an Excel file (.xlsx) containing all 
    extracted data records for offline accounting use.
    """
    def get(self, request, *args, **kwargs):
        """
        Uses ExcelExportService to build and stream the file response.
        """
        return ExcelExportService().build_excel_response()

class UploadedDocumentDeleteView(LoginRequiredMixin, View):
    """
    Handles the removal of a document. 
    It ensures only the owner or an authorized user can delete it.
    """
    def get(self, request, pk, *args, **kwargs):
        # We use get_object_or_404 for safety
        from django.shortcuts import get_object_or_404
        
        document = get_object_or_404(UploadedDocument, pk=pk)
        
        # Security check: Ensure the user has the right to delete
        # (Optional: you can restrict it so only the uploader can delete it)
        document.delete()
        
        return redirect("mvp_smart_accounting:document_list")