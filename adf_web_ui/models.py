import os
import time
import yaml

from typing import Type

from signal import SIGINT

from subprocess import Popen

from django.db.models import (
    Model,
    CharField,
    FileField,
    ForeignKey,
    IntegerField,
    FloatField,
    DateTimeField,
    CASCADE,
)
from django.db.models.signals import pre_delete, post_delete, pre_save
from django.dispatch import receiver
from django.conf import settings

from ADF.components.state_handlers import AbstractStateHandler
from ADF.components.implementers import ADFImplementer
from ADF.components.flow_config import ADFCollection
from ADF.components.data_structures import AbstractDataStructure

from .exceptions import ADFWebUIException, ConcurrentOrchestration


def attempt_file_field_delete(instance, attr):
    try:
        path = getattr(instance, attr).path
        getattr(instance, attr).delete(save=False)
        print(f"Successfully deleted {instance.__class__.__name__}::{attr} : {path} !")
    except Exception as e:
        print(
            f"WARNING : Failed to delete file {instance.__class__.__name__}::{attr}, got {e.__class__.__name__} : {str(e)}"
        )


def open_read_close(file_field: FileField) -> str:
    file_field.open()
    file_field.seek(0)
    ret = file_field.read().decode("utf-8")
    file_field.close()
    return ret


class FlowConfig(Model):
    name = CharField(max_length=50, unique=True)
    implementer_config_file = FileField()
    flow_config_file = FileField()
    created_at = DateTimeField(auto_now_add=True)
    last_updated = DateTimeField(auto_now=True)

    def get_implementer_class(self) -> Type[ADFImplementer]:
        return ADFImplementer.get_implementer_class(
            yaml.load(
                open(self.implementer_config_file.path, "r").read(), Loader=yaml.Loader
            )
        )

    def get_implementer(self) -> ADFImplementer:
        try:
            return ADFImplementer.from_config_path(self.implementer_config_file.path)
        except Exception as e:
            raise ADFWebUIException(
                "Implementer failed to load", f"{e.__class__.__name__}: {str(e)}"
            )

    def get_collection(self) -> ADFCollection:
        return ADFCollection.from_config_path(self.flow_config_file.path)

    def get_state_handler(self) -> AbstractStateHandler:
        return self.get_implementer().state_handler

    def get_collection_ads(self) -> AbstractDataStructure:
        return self.get_state_handler().to_collection_ads(self.get_collection())


@receiver(post_delete, sender=FlowConfig)
def post_delete_config_files(sender, instance, *args, **kwargs):
    attempt_file_field_delete(instance, "implementer_config_file")
    attempt_file_field_delete(instance, "flow_config_file")


class FlowOperation(Model):
    flow_config = ForeignKey(FlowConfig, on_delete=CASCADE)
    pid = IntegerField()
    subcommand = CharField(max_length=50)
    sub_args = CharField(max_length=500)
    label = CharField(max_length=50)
    start_time = FloatField()
    stdout = FileField()
    stderr = FileField()
    status = FileField()

    @property
    def status_summary(self) -> str:
        status = open_read_close(self.status).strip()
        if status == "0":
            return "DONE"
        elif status == "":
            return "RUNNING"
        elif status in ["USER_TERMINATED", "EXTERNALLY_TERMINATED"]:
            return status
        else:
            return "FAILED"

    def cmd(self, stdout_path: str, stderr_path: str, status_path: str) -> str:
        exe_path = ADFImplementer.get_exe_path()
        icp = self.flow_config.implementer_config_file.path
        ban_list = ["&;|>"]
        if any((banned in self.subcommand) or (banned in self.sub_args) for banned in ban_list):
            return "echo INJECTION DETECTED"
        return f"{exe_path} {icp} {self.subcommand} {self.sub_args} 1> {stdout_path} 2> {stderr_path} ; echo $? 1> {status_path} 2> {status_path}"

    def terminate_process(self):
        status = self.status_summary
        if status == "RUNNING":
            try:
                os.killpg(self.pid, SIGINT)
                open(self.status.path, "w").write("USER_TERMINATED")
                return "USER_TERMINATED"
            except ProcessLookupError:
                print(f"WARNING failled to kill pid {self.pid} !")
                open(self.status.path, "w").write("EXTERNALLY_TERMINATED")
                return "EXTERNALLY_TERMINATED"
        return status


def get_stdout_path(index: int) -> str:
    return settings.MEDIA_ROOT / f"stdout_{str(index).zfill(6)}.txt"


def get_stderr_path(index: int) -> str:
    return settings.MEDIA_ROOT / f"stderr_{str(index).zfill(6)}.txt"


def get_status_path(index: int) -> str:
    return settings.MEDIA_ROOT / f"status_{str(index).zfill(6)}.txt"


def get_log_index() -> int:
    index = 0
    while os.path.isfile(get_stdout_path(index)) or os.path.isfile(
        get_stderr_path(index)
    ):
        index += 1
    return index


@receiver(pre_save, sender=FlowOperation)
def launch_process(sender: Type[FlowOperation], instance: FlowOperation, **kwargs):
    if instance.pid is not None:
        return
    if instance.subcommand == "orchestrate":
        count = 0
        for orchestration in sender.objects.filter(
            subcommand="orchestrate", flow_config=instance.flow_config
        ):
            if orchestration.status_summary == "RUNNING":
                count += 1
        if count:
            raise ConcurrentOrchestration(instance.flow_config)
    log_index = get_log_index()
    stdout_path = get_stdout_path(log_index)
    stderr_path = get_stderr_path(log_index)
    status_path = get_status_path(log_index)
    open(status_path, "a").close()
    with open(stdout_path, "w") as out, open(stderr_path, "w") as err:
        process = Popen(
            instance.cmd(stdout_path, stderr_path, status_path),
            shell=True,
            preexec_fn=os.setsid,
        )
        instance.pid = process.pid
        instance.start_time = time.time()
        instance.stdout = os.path.relpath(stdout_path, settings.MEDIA_ROOT)
        instance.stderr = os.path.relpath(stderr_path, settings.MEDIA_ROOT)
        instance.status = os.path.relpath(status_path, settings.MEDIA_ROOT)


@receiver(pre_delete, sender=FlowOperation)
def terminate_process(sender, instance, **kwargs):
    instance.terminate_process()


@receiver(post_delete, sender=FlowOperation)
def post_delete_operation_files(sender, instance, *args, **kwargs):
    attempt_file_field_delete(instance, "stdout")
    attempt_file_field_delete(instance, "stderr")
    attempt_file_field_delete(instance, "status")
