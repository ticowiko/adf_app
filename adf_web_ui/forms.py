from django.forms import ModelForm

from .models import FlowConfig


class UploadFlowForm(ModelForm):
    class Meta:
        model = FlowConfig
        exclude = ["flowoperation_set"]
