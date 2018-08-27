from django.db import models
from django.utils import timezone

from django_cyverse_auth.models import Token


class AccessToken(models.Model):
    """
    Extend the django_cyverse_auth Token to add a name.
    These tokens are created and displayed in the Troposphere settings page to allow
    users to manage tokens used for external API access.
    """
    token = models.OneToOneField(Token, on_delete=models.CASCADE)
    name = models.CharField(max_length=128, null=False, blank=False)

    class Meta:
        db_table = "access_token"
        app_label = "core"

def create_access_token(user, token_name=None, token_expire=None, remote_ip=None, issuer=None):
    token = Token.objects.create(user=user, issuer=issuer)
    access_token = AccessToken.objects.create(token=token, name=token_name)
    return access_token
