"""
Required for django admin site.

"""

from django.contrib import admin
from django.contrib.auth.models import User


from auth.models import Token as AuthToken
from auth.models import UserProxy

admin.site.register(AuthToken)
admin.site.register(UserProxy)
