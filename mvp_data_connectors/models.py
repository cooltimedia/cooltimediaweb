"""
Scalable and Secure Models for the MVP Data Connectors application.

This module implements a dynamic structure to support multiple data sources 
(Instagram, Google Analytics, etc.) using Environment Variables for 
sensitive credentials to ensure production-grade security.

Author: Cooltimedia
Date: April 22, 2026
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

class ConnectorSource(models.Model):
    """
    Represents a specific data source configuration.
    
    Attributes:
        name (str): A friendly label for the connection.
        source_type (str): The platform type (e.g., INSTAGRAM, GA4).
        is_active (bool): Global switch to enable/disable this connector.
    """
    SOURCE_TYPES = [
        ('INSTAGRAM', 'Instagram Graph API'),
        ('GOOGLE_ANALYTICS', 'Google Analytics 4'),
    ]

    name = models.CharField(
        max_length=100, 
        help_text=_("Example: 'Main Brand - Instagram'")
    ) # I'm probably going to use a separate client model in the future.
    source_type = models.CharField(
        max_length=50, 
        choices=SOURCE_TYPES
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Connector Source")
        verbose_name_plural = _("Connector Sources")

    def __str__(self):
        return f"{self.name} ({self.get_source_type_display()})"


class ConnectorCredential(models.Model):
    """
    Stores non-sensitive configuration or references to environment variables.
    
    Instead of storing raw secrets, this model can store the 'Key Name' 
    of the Environment Variable where the actual secret is kept.
    """
    connector = models.ForeignKey(
        ConnectorSource, 
        on_delete=models.CASCADE, 
        related_name='credentials'
    )
    key = models.CharField(
        max_length=100,
        help_text=_("The parameter name (e.g., 'INSTAGRAM_APP_ID' or 'ENV_VAR_POINTER')")
    )
    value = models.TextField(
        help_text=_("The value or the name of the Environment Variable containing the secret.")
    )

    class Meta:
        unique_together = ('connector', 'key')
        verbose_name = _("Connector Credential")

    def __str__(self):
        return f"{self.key} for {self.connector.name}"


class BigQueryTarget(models.Model):
    """
    Destination settings for Google BigQuery.
    
    Credentials are not stored here; they are expected to be available in 
    the environment as GOOGLE_APPLICATION_CREDENTIALS or a custom variable.
    """
    connector = models.OneToOneField(
        ConnectorSource, 
        on_delete=models.CASCADE, 
        related_name='bq_destination'
    )
    project_id = models.CharField(max_length=255)
    dataset_id = models.CharField(max_length=255)
    table_id = models.CharField(max_length=255)
    
    env_variable_name = models.CharField(
        max_length=100,
        default="GOOGLE_APPLICATION_CREDENTIALS",
        help_text=_("The name of the Environment Variable that holds the JSON Service Account key.")
    )

    class Meta:
        verbose_name = _("BigQuery Target")
        verbose_name_plural = _("BigQuery Targets")

    def __str__(self):
        return f"BQ Destination: {self.dataset_id}.{self.table_id}"


class ExecutionLog(models.Model):
    """
    Unified audit trail for all data synchronization attempts.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    ]

    connector = models.ForeignKey(
        ConnectorSource, 
        on_delete=models.CASCADE,
        related_name='logs'
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    rows_affected = models.IntegerField(default=0)
    log_details = models.TextField(
        null=True, 
        blank=True, 
        help_text=_("Logs, error messages, or API response summaries.")
    )

    class Meta:
        ordering = ['-timestamp']
        verbose_name = _("Execution Log")
        verbose_name_plural = _("Execution Logs")