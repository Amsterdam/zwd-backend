from django.conf import settings
from django.contrib.auth import get_user_model
from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from mozilla_django_oidc.contrib.drf import OIDCAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.core.exceptions import PermissionDenied
import datetime
import time

DEFAULT_EMAIL = "admin@admin.com"
DEFAULT_USERNAME = "Local User"
DEFAULT_FIRST_NAME = "local"
DEFAULT_LAST_NAME = "user"


class OIDCAuthenticationBackend(OIDCAuthenticationBackend):
    def update_user(self, user, claims):
        user.first_name = claims.get("given_name", "")
        user.last_name = claims.get("family_name", "")
        user.username = claims.get("email")
        user.last_login = datetime.datetime.now(datetime.timezone.utc)
        user.save()
        return user

    def create_user(self, claims):
        user = super(OIDCAuthenticationBackend, self).create_user(claims)
        return self.update_user(user, claims)

    def validate_issuer(self, payload):
        issuer = self.get_settings("OIDC_OP_ISSUER")
        if not issuer == payload["iss"]:
            raise PermissionDenied(
                '"iss": %r does not match configured value for OIDC_OP_ISSUER: %r'
                % (payload["iss"], issuer)
            )

    def validate_audience(self, payload):
        trusted_audiences = self.get_settings("OIDC_TRUSTED_AUDIENCES", [])
        trusted_audiences = set(trusted_audiences)

        audience = payload["aud"]
        audience = set(audience)
        distrusted_audiences = audience.difference(trusted_audiences)
        if distrusted_audiences:
            raise PermissionDenied(
                '"aud" contains distrusted audiences: %r' % distrusted_audiences
            )

    def validate_expiry(self, payload):
        expire_time = payload["exp"]
        now = time.time()
        if now > expire_time:
            raise PermissionDenied(
                "Access-token is expired %r > %r" % (now, expire_time)
            )

    def validate_id_token(self, payload):
        """Validate the content of the id token as required by OpenID Connect 1.0

        This aims to fulfill point 2. 3. and 9. under section 3.1.3.7. ID Token
        Validation
        """
        self.validate_issuer(payload)
        self.validate_audience(payload)
        self.validate_expiry(payload)
        return payload

    def get_userinfo(self, access_token, id_token=None, payload=None):
        userinfo = self.verify_token(access_token)
        self.validate_id_token(userinfo)
        return userinfo


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
