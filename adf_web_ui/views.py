import os
import yaml

from wsgiref.util import FileWrapper

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.db.models import Prefetch
from django.http import HttpResponse

from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
    RetrieveDestroyAPIView,
)
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.views import APIView, Request, Response

from .forms import UploadFlowForm
from .models import FlowConfig, FlowOperation
from .serializers import FlowConfigSerializer, FlowOperationSerializer
from .exceptions import error_response, ADFWebUIException


@method_decorator(login_required, name="dispatch")
class FlowConfigListCreateAPIView(ListCreateAPIView):
    queryset = (
        FlowConfig.objects.prefetch_related(
            Prefetch(
                "flowoperation_set",
                queryset=FlowOperation.objects.order_by("-start_time"),
            )
        )
        .order_by("-last_updated")
        .all()
    )
    serializer_class = FlowConfigSerializer

    @error_response
    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        return redirect("flows_page")


@method_decorator(login_required, name="dispatch")
class FlowConfigRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    queryset = FlowConfig.objects.prefetch_related(
        Prefetch(
            "flowoperation_set", queryset=FlowOperation.objects.order_by("-start_time")
        )
    ).all()
    serializer_class = FlowConfigSerializer


@method_decorator(login_required, name="dispatch")
class FlowConfigFileUpdater(APIView):
    @error_response
    def put(self, request: Request, *args, **kwargs):
        flow_config: FlowConfig = get_object_or_404(
            FlowConfig, id=kwargs["flow_config_id"]
        )
        attr = kwargs["attr"]
        old_path = getattr(flow_config, attr).path
        setattr(flow_config, attr, request.FILES["file"])
        flow_config.save()
        try:
            os.remove(old_path)
            print(
                f"Successfully deleted old file at '{old_path}' when updating '{attr}' of flow config '{flow_config.name}'. "
            )
        except OSError:
            print(
                f"WARNING failed to delete old file at '{old_path}' when updating '{attr}' of flow config '{flow_config.name}'."
            )
        return Response()


@method_decorator(login_required, name="dispatch")
class FlowConfigPageView(View):
    @error_response
    def get(self, request):
        return render(request, "adf_web_ui/home.html", {"form": UploadFlowForm()})


@method_decorator(login_required, name="dispatch")
class FlowOperationLauncherAPIView(APIView):
    @error_response
    def get(self, request: Request, *args, **kwargs):
        return Response(
            FlowOperationSerializer(
                FlowOperation.objects.filter(
                    flow_config_id=request.query_params["flow_config_id"]
                ).order_by("-start_time")
                if "flow_config_id" in request.query_params
                else FlowOperation.objects.order_by("-start_time").all(),
                many=True,
            ).data
        )

    @error_response
    def post(self, request: Request, *args, **kwargs):
        required_params = {"flow_config_id", "subcommand", "sub_args", "label"}
        received_params = set(request.data.keys())
        if received_params != required_params:
            return Response(
                {
                    "required": sorted(list(required_params)),
                    "received": sorted(list(received_params)),
                },
                status=HTTP_400_BAD_REQUEST,
            )
        flow_config: FlowConfig = get_object_or_404(
            FlowConfig, id=request.data["flow_config_id"]
        )
        flow_operation = FlowOperation(
            flow_config=flow_config,
            subcommand=request.data["subcommand"],
            sub_args=request.data["sub_args"].replace(
                "__fcp__", flow_config.flow_config_file.path
            ),
            label=request.data["label"],
        )
        flow_operation.save()
        return Response({"flow_operation_id": flow_operation.id})


@method_decorator(login_required, name="dispatch")
class FlowOperationRetrieveDestroyAPIView(RetrieveDestroyAPIView):
    queryset = FlowOperation.objects.all()
    serializer_class = FlowOperationSerializer


@method_decorator(login_required, name="dispatch")
class FlowOperationKillerAPIView(APIView):
    @error_response
    def put(self, request: Request, *args, **kwargs):
        return Response(
            {
                "status": get_object_or_404(
                    FlowOperation,
                    pk=kwargs["pk"],
                ).terminate_process()
            }
        )


@method_decorator(login_required, name="dispatch")
class FlowStateAPIView(APIView):
    @error_response
    def get(self, request: Request, *args, **kwargs):
        flow_config: FlowConfig = get_object_or_404(
            FlowConfig, id=kwargs["flow_config_id"]
        )
        try:
            ads = flow_config.get_collection_ads()
        except Exception as e:
            print(
                f"WARNING : Failed to load collection state, got {e.__class__.__name__}: {str(e)}"
            )
            raise ADFWebUIException(
                "Failed to load collection state", f"{e.__class__.__name__}: {str(e)}"
            )
        if {"flow_name", "step_name"} <= kwargs.keys():
            response = {}
            version = (
                flow_config.get_collection()
                .get_step(kwargs["flow_name"], kwargs["step_name"])
                .version
            )
            try:
                results = ads[
                    (ads["flow_name"] == kwargs["flow_name"])
                    & (ads["step_name"] == kwargs["step_name"])
                    & (ads["version"] == version)
                ][["batch_id", "status"]].to_list_of_dicts()
            except Exception as e:
                print(
                    "WARNING : failed to fetch batch ids, are you sure the state handler is set up ?"
                )
                print(f"{e.__class__.__name__} : {str(e)}")
                return Response({})
            for status in results:
                response.setdefault(status["status"], []).append(status["batch_id"])
            return Response(response)
        else:
            response = {}
            try:
                results = ads.group_by(
                    ["flow_name", "step_name", "version", "status"],
                    {"count": (lambda ads: ads.count(), int)},
                ).to_list_of_dicts()
            except Exception as e:
                print(
                    "WARNING : failed to fetch batch ids, are you sure the state handler is set up ?"
                )
                print(f"{e.__class__.__name__} : {str(e)}")
                return Response({})
            for counts in results:
                response.setdefault(counts["flow_name"], {}).setdefault(
                    counts["step_name"], {}
                ).setdefault(counts["version"], {})[counts["status"]] = counts["count"]
            return Response(response)


@method_decorator(login_required, name="dispatch")
class FlowDonwstreamAPIView(APIView):
    @error_response
    def get(self, request: Request, *args, **kwargs):
        flow_config: FlowConfig = get_object_or_404(
            FlowConfig, id=kwargs["flow_config_id"]
        )
        state_handler = flow_config.get_state_handler()
        step = flow_config.get_collection().get_step(
            kwargs["flow_name"], kwargs["step_name"]
        )
        try:
            batch_ids = (
                [kwargs["batch_id"]]
                if "batch_id" in kwargs
                else (
                    state_handler.get_step_all(step)
                    if (request.query_params.get("status") is None)
                    else state_handler.get_step_per_status(
                        step, request.query_params.get("status")
                    )
                )
            )
        except Exception as e:
            print(
                "WARNING : failed to fetch batch ids, are you sure the state handler is set up ?"
            )
            print(f"{e.__class__.__name__} : {str(e)}")
            return Response([])
        try:
            downstream = state_handler.get_downstream(step, batch_ids)
        except Exception as e:
            print(
                "WARNING : failed to fetch downstream, are you sure the state handler is set up ?"
            )
            print(f"{e.__class__.__name__} : {str(e)}")
            return Response([])
        return Response([[step.to_dict(), batch_ids] for step, batch_ids in downstream])


@method_decorator(login_required, name="dispatch")
class FlowBatchInfoAPIView(APIView):
    @error_response
    def get(self, request: Request, *args, **kwargs):
        flow_config: FlowConfig = get_object_or_404(
            FlowConfig, id=kwargs["flow_config_id"]
        )
        state_handler = flow_config.get_state_handler()
        step = flow_config.get_collection().get_step(
            kwargs["flow_name"], kwargs["step_name"]
        )
        try:
            batch_info = state_handler.get_batch_info(step, kwargs["batch_id"])
        except Exception as e:
            print(
                "WARNING : failed to fetch batch info, are you sure the state handler is set up ?"
            )
            print(f"{e.__class__.__name__} : {str(e)}")
            return Response({})
        return Response(batch_info)


@method_decorator(login_required, name="dispatch")
class FlowBatchDataAPIView(APIView):
    @error_response
    def get(self, request: Request, *args, **kwargs):
        flow_config: FlowConfig = get_object_or_404(
            FlowConfig, id=kwargs["flow_config_id"]
        )
        step = flow_config.get_collection().get_step(
            kwargs["flow_name"], kwargs["step_name"]
        )
        if step.get_output_steps():
            return Response([])
        return Response(
            flow_config.get_implementer()
            .layers[step.layer]
            .read_batch_data(step, kwargs["batch_id"])
            .limit(10)
            .to_list_of_dicts()
        )


@method_decorator(login_required, name="dispatch")
class GeneratePrebuiltAPIView(APIView):
    @error_response
    def get(self, request: Request, *args, **kwargs):
        flow_config: FlowConfig = get_object_or_404(
            FlowConfig, id=kwargs["flow_config_id"]
        )
        response = HttpResponse(
            yaml.dump(
                flow_config.get_implementer().output_prebuilt_config(
                    flow_config.implementer_config_file.path
                ),
                Dumper=yaml.Dumper,
            ),
            content_type="text/plain",
        )
        response['Content-Disposition'] = 'attachment; filename=prebuilt.yaml'
        return response
