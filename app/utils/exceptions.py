from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


class BaseException(Exception):
    default_message = "Error"

    def __init__(self, resp=None):
        resp = resp if resp else self.default_message
        self.args = (resp,)
        self.message = resp


class NotFoundException(BaseException):
    default_message = "Dit object is niet gevonden."


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, NotFoundException):
        return Response(
            {"message": exc.message},
            status=status.HTTP_404_NOT_FOUND,
        )

    if response is not None:
        response.data["status_code"] = response.status_code

    return response
