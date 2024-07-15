from mozilla_django_oidc.auth import OIDCAuthenticationBackend

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