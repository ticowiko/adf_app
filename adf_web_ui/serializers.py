import os
import datetime

from rest_framework.serializers import (
    ModelSerializer,
    SerializerMethodField,
)

from ADF.components.flow_config import ADFCollection
from ADF.exceptions import InvalidADFCollection

from .models import FlowConfig, FlowOperation, open_read_close


def serialize_datetime(dt: datetime.datetime):
    return f"{dt.day:02}/{dt.month:02}/{dt.year:04} {dt.hour:02}:{dt.minute:02}:{dt.second:02}"


class FlowOperationSerializer(ModelSerializer):
    stdout_details = SerializerMethodField()
    stderr_details = SerializerMethodField()
    status_details = SerializerMethodField()
    status_summary = SerializerMethodField()
    end_time = SerializerMethodField()
    start_time_pretty = SerializerMethodField()
    end_time_pretty = SerializerMethodField()

    class Meta:
        model = FlowOperation
        fields = (
            "id",
            "flow_config_id",
            "pid",
            "subcommand",
            "sub_args",
            "label",
            "stdout",
            "stderr",
            "status",
            "start_time",
            "end_time",
            "stdout_details",
            "stderr_details",
            "status_details",
            "status_summary",
            "start_time_pretty",
            "end_time_pretty",
        )

    def get_stdout_details(self, instance: FlowOperation):
        return open_read_close(instance.stdout)

    def get_stderr_details(self, instance: FlowOperation):
        return open_read_close(instance.stderr)

    def get_status_details(self, instance: FlowOperation):
        return open_read_close(instance.status)

    def get_status_summary(self, instance: FlowOperation):
        return instance.status_summary

    def get_end_time(self, instance: FlowOperation):
        if instance.status_summary is "RUNNING":
            return None
        return os.path.getmtime(instance.status.path)

    def get_start_time_pretty(self, instance: FlowOperation):
        return serialize_datetime(datetime.datetime.fromtimestamp(instance.start_time))

    def get_end_time_pretty(self, instance: FlowOperation):
        if instance.status_summary is "RUNNING":
            return None
        return serialize_datetime(
            datetime.datetime.fromtimestamp(os.path.getmtime(instance.status.path))
        )


class FlowConfigSerializer(ModelSerializer):
    implementer_class = SerializerMethodField()
    implementer_config_details = SerializerMethodField()
    flow_config_details = SerializerMethodField()
    flow_dag = SerializerMethodField()
    flowoperation_set = FlowOperationSerializer(required=False, many=True)

    class Meta:
        model = FlowConfig
        fields = (
            "id",
            "name",
            "implementer_class",
            "implementer_config_file",
            "flow_config_file",
            "implementer_config_details",
            "flow_config_details",
            "flow_dag",
            "flowoperation_set",
        )

    def get_implementer_class(self, instance: FlowConfig) -> str:
        try:
            return instance.get_implementer_class().__name__
        except Exception as e:
            print(f"WARNING : failed to get implementer class, got {e.__class__.__name__}: {str(e)}")
            return "Improper config"

    def get_implementer_config_details(self, instance: FlowConfig) -> str:
        return open_read_close(instance.implementer_config_file)

    def get_flow_config_details(self, instance: FlowConfig) -> str:
        return open_read_close(instance.flow_config_file)

    def get_flow_dag(self, instance: FlowConfig) -> dict:
        try:
            return ADFCollection.from_config_path(
                instance.flow_config_file.path
            ).to_dict()
        except InvalidADFCollection as e:
            return {"errors": {"validation_errors": e.errs}}
        except Exception as e:
            return {
                "errors": {
                    "uncaught_error_class": e.__class__.__name__,
                    "uncaught_error_content": str(e),
                },
            }
