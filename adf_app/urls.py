from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf.urls.static import static
from django.conf import settings


urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("django.contrib.auth.urls")),
    path("ui/", include("adf_web_ui.urls")),
    path("", RedirectView.as_view(url="ui/")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
