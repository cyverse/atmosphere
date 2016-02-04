from rest_framework import serializers

from threepio import logger

from core.models.identity import Identity
from core.models.user import AtmosphereUser

from .identity_related_field import IdentityRelatedField


class AtmoUserSerializer(serializers.ModelSerializer):
    selected_identity = IdentityRelatedField(
        queryset=Identity.objects.all())

    def validate_selected_identity(self, selected_identity):
        """
        Check that profile is an identitymember & providermember
        Returns the dict of attrs
        """
        user = self.instance
        logger.info("Validating identity for %s" % user)
        logger.debug(selected_identity)
        groups = user.group_set.all()
        for g in groups:
            for id_member in g.identity_memberships.all():
                if id_member.identity == selected_identity:
                    return selected_identity
        raise serializers.ValidationError( 
                "User is not a member of selected_identity: %s" % selected_identity)

    class Meta:
        model = AtmosphereUser
        exclude = ('id', 'password')
