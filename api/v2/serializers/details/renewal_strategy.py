from rest_framework import serializers

class RenewalStrategySerializer(serializers.Serializer):

    id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    compute_allowed = serializers.SerializerMethodField()
    renewed_in_days = serializers.SerializerMethodField()
    external = serializers.SerializerMethodField()

    def get_name(self,strategy):
        return strategy[0]

    def get_id(self,strategy):
        return strategy[1]['id']

    def get_compute_allowed(self,strategy):
        return strategy[1]['compute_allowed']

    def get_renewed_in_days(self,strategy):
        return strategy[1]['renewed_in_days']

    def get_external(self, strategy):
        return strategy[1]['external']

    class Meta:
        fields = (
            'id',
            'name',
            'compute_allowed',
            'renewed_in_days',
            'external'
        )
