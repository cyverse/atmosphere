"""
Required for django admin site.

"""

from django.contrib import admin


from authentication.models import Token as AuthToken
from authentication.models import UserProxy

admin.site.register(AuthToken)
admin.site.register(UserProxy)
