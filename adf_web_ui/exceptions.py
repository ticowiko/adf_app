import traceback

from typing import Callable

from rest_framework.views import Response


class ADFWebUIException(Exception):
    def __init__(self, title, message):
        self.title = title
        self.message = message

    def to_response(self) -> Response:
        return Response({"title": self.title, "message": self.message}, status=400)


class ConcurrentOrchestration(ADFWebUIException):
    def __init__(self, flow_config):
        super().__init__(
            title="Concurrent Orchestration Requested",
            message=f"Flow config {flow_config.name} already has an orchestrator running !",
        )


def error_response(func: Callable):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ADFWebUIException as e:
            return e.to_response()
        except Exception as e:
            print(f"{'*'*10} UNCAUGHT ERROR {'*'*10}")
            print(traceback.format_exc())
            print('*'*36)
            return Response({"title": "Uncaught error", "message": f"{e.__class__.__name__}: {str(e)}"}, status=400)
    return wrapper
