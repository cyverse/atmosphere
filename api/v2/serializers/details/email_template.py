from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from core.models.template import EmailTemplate


class EmailTemplateSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        raise ValidationError("Cannot create new email templates via API")

    class Meta:
        model = EmailTemplate
