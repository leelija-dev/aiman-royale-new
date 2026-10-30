from rest_framework.authentication import SessionAuthentication
class SafeSessionAuthentication(SessionAuthentication):
    def authenticate(self,request):
        if request.method not in ['GET','HEAD','OPTIONS']:self.enforce_csrf(request)
        return super().authenticate(request)
def exception_handler(exc,context):
    from rest_framework.views import exception_handler as default_handler
    from rest_framework.exceptions import ValidationError
    from django.core.exceptions import ValidationError as DjangoValidationError
    if isinstance(exc,DjangoValidationError):exc=ValidationError(exc.messages)
    response=default_handler(exc,context)
    if response is not None:response.data={'error':response.data}
    return response
