from django.contrib import admin
from .models import (
    AppProcessingLog,
    BranchSetting,
    QueueTicket,
    ServiceType,
    TicketCall,
    TicketSequence,
)


class ServiceTypeInline(admin.TabularInline):
    model = ServiceType
    extra = 0
    fields = (
        "name",
        "slug",
        "prefix",
        "is_active",
        "use_branch_reset_policy",
        "reset_policy",
        "average_service_time_minutes",
    )
    show_change_link = True


@admin.register(BranchSetting)
class BranchSettingAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "is_active",
        "is_digital_only",
        "auto_print",
        "has_priority_lane",
        "reset_policy",
        "max_call_attempts",
        "call_interval_seconds",
        "updated_at",
    )
    list_filter = (
        "is_active",
        "is_digital_only",
        "auto_print",
        "requires_identification",
        "has_priority_lane",
        "enable_qr_tracking",
        "allow_customer_cancel",
        "show_estimated_wait_time",
        "reset_policy",
    )
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ServiceTypeInline]

    fieldsets = (
        ("Basic Information", {
            "fields": ("name", "slug", "is_active")
        }),
        ("Queue Flow", {
            "fields": (
                "is_digital_only",
                "auto_print",
                "requires_identification",
                "has_priority_lane",
            )
        }),
        ("Ticket Numbering", {
            "fields": ("reset_policy",)
        }),
        ("Call Configuration", {
            "fields": (
                "max_call_attempts",
                "call_interval_seconds",
            )
        }),
        ("Monitoring", {
            "fields": ("critical_wait_threshold_minutes",)
        }),
        ("Customer Tracking and Public Display", {
            "fields": (
                "enable_qr_tracking",
                "allow_customer_cancel",
                "show_estimated_wait_time",
                "public_message",
                "secondary_message",
            )
        }),
        ("Audit", {
            "fields": ("created_at", "updated_at")
        }),
    )

    readonly_fields = ("created_at", "updated_at")


@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "branch",
        "prefix",
        "is_active",
        "use_branch_reset_policy",
        "reset_policy",
        "average_service_time_minutes",
        "updated_at",
    )
    list_filter = (
        "branch",
        "is_active",
        "use_branch_reset_policy",
        "reset_policy",
    )
    search_fields = ("name", "slug", "prefix", "branch__name")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("branch",)

    fieldsets = (
        ("Basic Information", {
            "fields": (
                "branch",
                "name",
                "slug",
                "prefix",
                "description",
                "is_active",
            )
        }),
        ("Queue Configuration", {
            "fields": (
                "use_branch_reset_policy",
                "reset_policy",
                "average_service_time_minutes",
            )
        }),
        ("Audit", {
            "fields": ("created_at", "updated_at")
        }),
    )

    readonly_fields = ("created_at", "updated_at")


class TicketCallInline(admin.TabularInline):
    model = TicketCall
    extra = 0
    fields = (
        "attempt_number",
        "result",
        "called_by",
        "notes",
        "created_at",
    )
    readonly_fields = ("created_at",)
    autocomplete_fields = ("called_by",)


@admin.register(QueueTicket)
class QueueTicketAdmin(admin.ModelAdmin):
    list_display = (
        "ticket_code",
        "branch",
        "service_type",
        "number",
        "status",
        "is_priority",
        "people_ahead",
        "estimated_wait_minutes",
        "call_attempts",
        "assigned_agent",
        "created_at",
    )
    list_filter = (
        "branch",
        "service_type",
        "status",
        "is_priority",
        "created_at",
    )
    search_fields = (
        "ticket_code",
        "internal_token",
        "customer_name",
        "customer_id",
    )
    autocomplete_fields = (
        "branch",
        "service_type",
        "assigned_agent",
    )
    readonly_fields = (
        "ticket_code",
        "internal_token",
        "number",
        "people_ahead",
        "estimated_wait_minutes",
        "created_at",
        "updated_at",
    )
    inlines = [TicketCallInline]

    fieldsets = (
        ("Identifiers", {
            "fields": (
                "ticket_code",
                "internal_token",
                "number",
            )
        }),
        ("Queue Information", {
            "fields": (
                "branch",
                "service_type",
                "status",
                "is_priority",
                "people_ahead",
                "estimated_wait_minutes",
            )
        }),
        ("Customer Information", {
            "fields": (
                "customer_name",
                "customer_id",
            )
        }),
        ("Call and Service Lifecycle", {
            "fields": (
                "call_attempts",
                "called_at",
                "service_start_at",
                "finished_at",
                "cancelled_at",
                "missed_at",
                "assigned_agent",
            )
        }),
        ("Audit", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )


@admin.register(TicketSequence)
class TicketSequenceAdmin(admin.ModelAdmin):
    list_display = (
        "branch",
        "service_type",
        "sequence_date",
        "last_number",
        "updated_at",
    )
    list_filter = (
        "branch",
        "service_type",
        "sequence_date",
    )
    search_fields = (
        "branch__name",
        "service_type__name",
        "service_type__prefix",
    )
    autocomplete_fields = (
        "branch",
        "service_type",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(TicketCall)
class TicketCallAdmin(admin.ModelAdmin):
    list_display = (
        "ticket",
        "attempt_number",
        "result",
        "called_by",
        "created_at",
    )
    list_filter = (
        "result",
        "created_at",
    )
    search_fields = (
        "ticket__ticket_code",
        "notes",
    )
    autocomplete_fields = (
        "ticket",
        "called_by",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(AppProcessingLog)
class AppProcessingLogAdmin(admin.ModelAdmin):
    list_display = (
        "level",
        "action",
        "branch",
        "service_type",
        "ticket",
        "user",
        "created_at",
    )
    list_filter = (
        "level",
        "branch",
        "service_type",
        "created_at",
    )
    search_fields = (
        "action",
        "ticket__ticket_code",
        "branch__name",
        "service_type__name",
    )
    autocomplete_fields = (
        "branch",
        "service_type",
        "ticket",
        "user",
    )
    readonly_fields = (
        "payload",
        "created_at",
        "updated_at",
    )