from core.models.tag import Tag
from core.models import AtmosphereUser
from rest_framework import serializers


class TagSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(slug_field='username', queryset=AtmosphereUser.objects.all())
    description = serializers.CharField(required=False)

    class Meta:
        model = Tag