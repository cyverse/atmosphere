from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from core.models.template import EmailTemplate


class EmailTemplateSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        raise ValidationError("Cannot create new email templates via API")
        if 'created_by' not in validated_data:
            request = self.context.get('request')
            if request and request.user:
                validated_data['created_by'] = request.user
        return super(EmailTemplateSerializer, self).create(validated_data)

    class Meta:
        model = EmailTemplate
