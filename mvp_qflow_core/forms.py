"""
Forms for the QFlow MVP application.

These forms are intentionally focused on input collection and validation.
Business logic and ticket lifecycle operations should remain in services.
"""

from django import forms

from mvp_qflow_core.models import BranchSetting, ServiceType, TicketStatus

class ServiceTypeChoiceField(forms.ModelChoiceField):
    """
    Custom ModelChoiceField to refine the display of ServiceType instances.
    
    In a multi-tenant or multi-branch environment, the default __str__ 
    representation often includes the branch name for administrative clarity. 
    This field overrides that behavior to provide a cleaner, customer-facing 
    label by only exposing the service name.
    """
    def label_from_instance(self, obj):
        """
        Returns the display label for the service.
        
        Args:
            obj (ServiceType): The service instance being rendered.
            
        Returns:
            str: The clean name of the service (e.g., 'Priority' instead of 
                 'Priority - Branch Name').
        """
        return obj.name
    
    
class KioskTicketForm(forms.Form):
    """
    Form used by the kiosk flow to create a new queue ticket.

    The form is initialized with a specific branch so it can:
    - limit available services to active services in that branch
    - adapt validation rules based on branch configuration
    """

    service_type = ServiceTypeChoiceField(
        queryset=ServiceType.objects.none(),
        empty_label="Select a service",
        label="Service",
        widget=forms.RadioSelect(attrs={
            "class": "peer sr-only", 
        }),
    )
    customer_name = forms.CharField(
        max_length=100,
        required=False,
        label="Customer name",
        widget=forms.TextInput(attrs={
            "class": "block w-full rounded-md border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 transition focus:border-emerald-700 focus:outline-none focus:ring-2 focus:ring-emerald-500/20",
            "placeholder": "Optional customer name",
        }),
    )
    customer_id = forms.CharField(
        max_length=30,
        required=False,
        label="Identification",
        widget=forms.TextInput(attrs={
            "class": "block w-full rounded-md border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 transition focus:border-emerald-700 focus:outline-none focus:ring-2 focus:ring-emerald-500/20",
            "placeholder": "Optional Identification",
        }),
    )
    is_priority = forms.BooleanField(
        required=False,
        label="Priority attention",
        widget=forms.TextInput(attrs={
            "class": "sr-only peer",
        }),
    )

    def __init__(self, *args, branch: BranchSetting, **kwargs):
        """
        Initializes the form using the provided branch configuration.

        Args:
            branch (BranchSetting): Active branch used to configure the form.
        """
        super().__init__(*args, **kwargs)

        if not branch:
            raise ValueError("branch is required for KioskTicketForm.")

        if not isinstance(branch, BranchSetting):
            raise ValueError("branch must be an instance of BranchSetting.")

        self.branch = branch

        self.fields["service_type"].queryset = ServiceType.objects.filter(
            branch=branch,
            is_active=True,
        ).order_by("name")

        self.fields["customer_name"].widget.attrs.update({
            "placeholder": "Optional customer name",
            "class": "block w-full rounded-md border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 transition focus:border-emerald-700 focus:outline-none focus:ring-2 focus:ring-emerald-500/20",
        })
        self.fields["customer_id"].widget.attrs.update({
            "placeholder": "Identification number",
            "class": "block w-full rounded-md border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 transition focus:border-emerald-700 focus:outline-none focus:ring-2 focus:ring-emerald-500/20",
        })
        self.fields["service_type"].widget.attrs.update({
            "class": "peer sr-only",
        })
        self.fields["is_priority"].widget.attrs.update({
            "class": "sr-only peer",
        })

        if self.branch.requires_identification:
            self.fields["customer_id"].required = True
            self.fields["customer_id"].help_text = (
                "Identification is required for this branch."
            )

        if not self.branch.has_priority_lane:
            self.fields["is_priority"].help_text = (
                "Priority tickets are still allowed and will be handled with operational priority."
            )
        else:
            self.fields["is_priority"].help_text = (
                "Enable this option for priority queue attention."
            )

    def clean_service_type(self):
        """
        Validates that the selected service belongs to the current branch
        and is active.
        """
        service_type = self.cleaned_data.get("service_type")

        if not service_type:
            raise forms.ValidationError("You must select a service.")

        if service_type.branch_id != self.branch.id:
            raise forms.ValidationError(
                "The selected service does not belong to this branch."
            )

        if not service_type.is_active:
            raise forms.ValidationError(
                "The selected service is not active."
            )

        return service_type

    def clean_customer_name(self):
        """
        Normalizes the optional customer name value.
        """
        customer_name = self.cleaned_data.get("customer_name")

        if customer_name is None:
            return None

        customer_name = customer_name.strip()
        return customer_name or None

    def clean_customer_id(self):
        """
        Normalizes and validates the customer identification value.
        """
        customer_id = self.cleaned_data.get("customer_id")

        if customer_id is None:
            customer_id = ""

        customer_id = customer_id.strip()

        if self.branch.requires_identification and not customer_id:
            raise forms.ValidationError(
                "Identification is required for this branch."
            )

        return customer_id or None

    def clean_is_priority(self):
        """
        Normalizes the priority flag.
        """
        is_priority = self.cleaned_data.get("is_priority", False)
        return bool(is_priority)

    def clean(self):
        """
        Performs cross-field validation for kiosk ticket creation.
        """
        cleaned_data = super().clean()

        service_type = cleaned_data.get("service_type")
        customer_id = cleaned_data.get("customer_id")

        if self.branch.requires_identification and not customer_id:
            self.add_error(
                "customer_id",
                "Identification is required for this branch."
            )

        if service_type and service_type.branch_id != self.branch.id:
            self.add_error(
                "service_type",
                "The selected service does not belong to this branch."
            )

        return cleaned_data

    def get_creation_payload(self, created_by=None) -> dict:
        """
        Returns a clean payload dictionary ready to be adapted into
        TicketCreationData.

        Args:
            created_by: Optional authenticated user.

        Returns:
            dict: Cleaned payload for ticket creation.
        """
        if not self.is_valid():
            raise ValueError(
                "Form must be valid before calling get_creation_payload()."
            )

        return {
            "branch": self.branch,
            "service_type": self.cleaned_data["service_type"],
            "customer_name": self.cleaned_data.get("customer_name"),
            "customer_id": self.cleaned_data.get("customer_id"),
            "is_priority": self.cleaned_data.get("is_priority", False),
            "created_by": created_by,
        }


class TicketTrackingCancelForm(forms.Form):
    """
    Simple confirmation form for ticket cancellation from the tracking page.

    This form helps prevent accidental cancellations and gives the UI
    a clear validation surface.
    """

    confirm_cancel = forms.BooleanField(
        required=True,
        label="I confirm that I want to cancel this ticket.",
        widget=forms.TextInput(attrs={
            "class": "form-control",
        }),
    )

    def __init__(self, *args, ticket=None, **kwargs):
        """
        Initializes the form with the target ticket.

        Args:
            ticket: QueueTicket instance associated with the cancellation flow.
        """
        super().__init__(*args, **kwargs)
        self.ticket = ticket

        self.fields["confirm_cancel"].widget.attrs.update({
            "class": "form-check-input",
        })

    def clean(self):
        """
        Validates that the ticket can still be cancelled from the UI perspective.
        """
        cleaned_data = super().clean()

        if not self.ticket:
            raise forms.ValidationError("A valid ticket is required.")

        if self.ticket.status not in {TicketStatus.WAITING, TicketStatus.CALLED}:
            raise forms.ValidationError(
                "This ticket can no longer be cancelled."
            )

        return cleaned_data