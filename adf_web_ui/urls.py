from django.urls import path, re_path, include
from django.views.generic.base import RedirectView

from .views import (
    FlowConfigListCreateAPIView,
    FlowConfigRetrieveUpdateDestroyAPIView,
    FlowConfigPageView,
    FlowOperationLauncherAPIView,
    FlowOperationRetrieveDestroyAPIView,
    FlowOperationKillerAPIView,
    FlowStateAPIView,
    FlowDonwstreamAPIView,
    FlowBatchInfoAPIView,
    FlowBatchDataAPIView,
    FlowConfigFileUpdater,
    GeneratePrebuiltAPIView,
)

apipatterns = [
    path("auth/", include("rest_framework.urls")),
    re_path("^flow_configs/$", FlowConfigListCreateAPIView.as_view()),
    re_path(
        "^flow_configs/(?P<pk>.+)/$", FlowConfigRetrieveUpdateDestroyAPIView.as_view()
    ),
    re_path(
        "^flow_configs_file_update/(?P<flow_config_id>.+)/(?P<attr>.+)/$", FlowConfigFileUpdater.as_view()
    ),
    re_path(
        "^flow_operations/$",
        FlowOperationLauncherAPIView.as_view(),
    ),
    re_path(
        "^flow_operations/(?P<pk>.+)/$",
        FlowOperationRetrieveDestroyAPIView.as_view(),
    ),
    re_path(
        "^flow_operations_kill/(?P<pk>.+)/$",
        FlowOperationKillerAPIView.as_view(),
    ),
    re_path(
        "^flow_states/(?P<flow_config_id>.+)/(?P<flow_name>.+)/(?P<step_name>.+)/$",
        FlowStateAPIView.as_view(),
    ),
    re_path(
        "^flow_states/(?P<flow_config_id>.+)/$",
        FlowStateAPIView.as_view(),
    ),
    re_path(
        "^flow_downstreams/(?P<flow_config_id>.+)/(?P<flow_name>.+)/(?P<step_name>.+)/(?P<batch_id>.+)/",
        FlowDonwstreamAPIView.as_view(),
    ),
    re_path(
        "^flow_downstreams/(?P<flow_config_id>.+)/(?P<flow_name>.+)/(?P<step_name>.+)/",
        FlowDonwstreamAPIView.as_view(),
    ),
    re_path(
        "^flow_batch_info/(?P<flow_config_id>.+)/(?P<flow_name>.+)/(?P<step_name>.+)/(?P<batch_id>.+)/",
        FlowBatchInfoAPIView.as_view(),
    ),
    re_path(
        "^flow_batch_data/(?P<flow_config_id>.+)/(?P<flow_name>.+)/(?P<step_name>.+)/(?P<batch_id>.+)/",
        FlowBatchDataAPIView.as_view(),
    ),
    re_path(
        "^generate_prebuilt/(?P<flow_config_id>.+)/$",
        GeneratePrebuiltAPIView.as_view(),
    ),
]

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="flows_page")),
    re_path("^api/", include(apipatterns)),
    re_path("^flow_configs/$", FlowConfigPageView.as_view(), name="flows_page"),
]
