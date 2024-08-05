from django.conf import settings
from django.contrib.auth import get_user_model
from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from mozilla_django_oidc.contrib.drf import OIDCAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication

DEFAULT_EMAIL = "admin@admin.com"
DEFAULT_USERNAME = "Local User"
DEFAULT_FIRST_NAME = "local"
DEFAULT_LAST_NAME = "user"


class OIDCAuthenticationBackend(OIDCAuthenticationBackend):
    def update_user(self, user, claims):
        user.first_name = claims.get("given_name", "")
        user.last_name = claims.get("family_name", "")
        user.username = claims.get("email")
        user.save()
        return user

    def create_user(self, claims):
        user = super(OIDCAuthenticationBackend, self).create_user(claims)
        return self.update_user(user, claims)


class DevelopmentAuthenticationBackend(OIDCAuthenticationBackend):
    def authenticate(self, request):
        user_model = get_user_model()
        try:
            user = user_model.objects.get(email=DEFAULT_EMAIL)
        except user_model.DoesNotExist:
            user = user_model.objects.create_user(DEFAULT_EMAIL)

        user.first_name = DEFAULT_FIRST_NAME
        user.last_name = DEFAULT_LAST_NAME
        user.save()
        return user


if settings.LOCAL_DEVELOPMENT_AUTHENTICATION:
    AuthenticationBackend = DevelopmentAuthenticationBackend
    AuthenticationClass = JWTAuthentication
else:
    AuthenticationBackend = OIDCAuthenticationBackend
    AuthenticationClass = OIDCAuthentication
