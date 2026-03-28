"""
URL Configuration for the Smart Accounting Automation MVP.
Defines the routing for authentication, dashboard visualization, 
document management, and Excel data exportation.
"""

from django.urls import path
from .views import (
    DashboardView,
    LoginView,
    ExportParsedDocumentsExcelView,
    UploadedDocumentCreateView,
    UploadedDocumentDetailView,
    UploadedDocumentListView,
    UploadedDocumentDeleteView,
)

app_name = "mvp_smart_accounting"

urlpatterns = [
    # Authentication
    path("login/", LoginView.as_view(), name="login"),
    
    # Main Interface
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    
    # Document Management
    path("documents/", UploadedDocumentListView.as_view(), name="document_list"),
    path("documents/upload/", UploadedDocumentCreateView.as_view(), name="document_upload"),
    path("documents/<int:pk>/", UploadedDocumentDetailView.as_view(), name="document_detail"),
    path("documents/<int:pk>/delete/", UploadedDocumentDeleteView.as_view(), name="document_delete"),
    
    # Data Exportation
    path(
        "exports/documents.xlsx", 
        ExportParsedDocumentsExcelView.as_view(), 
        name="documents_excel_export"
    ),
]