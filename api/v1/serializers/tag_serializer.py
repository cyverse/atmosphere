from core.models.tag import Tag
from core.models import AtmosphereUser
from rest_framework import serializers


class TagSerializer_POST(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(
        slug_field='username',
        queryset=AtmosphereUser.objects.all())
    description = serializers.CharField(required=False)
    name = serializers.CharField()

    class Meta:
        model = Tag


class TagSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(
        slug_field='username',
        queryset=AtmosphereUser.objects.all())
    description = serializers.CharField(required=False)
    # TODO: Should not be changed until the API no longer uses tag_name/tag_slug for URLs
    # TODO: Should probably use UUIDs in the API
    name = serializers.CharField(read_only=True)

    class Meta:
        model = Tag
