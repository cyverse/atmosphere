from core.models.user import AtmosphereUser
from rest_framework import serializers
from threepio import logger
from .identity_related_field import IdentityRelatedField


class AtmoUserSerializer(serializers.ModelSerializer):
    selected_identity = IdentityRelatedField(source='select_identity')

    def validate_selected_identity(self, attrs, source):
        """
        Check that profile is an identitymember & providermember
        Returns the dict of attrs
        """
        #Short-circut if source (identity) not in attrs
        logger.debug(attrs)
        logger.debug(source)
        if 'selected_identity' not in attrs:
            return attrs
        user = self.object.user
        logger.info("Validating identity for %s" % user)
        selected_identity = attrs['selected_identity']
        logger.debug(selected_identity)
        groups = user.group_set.all()
        import ipdb;ipdb.set_trace()
        for g in groups:
            for id_member in g.identitymembership_set.all():
                if id_member.identity == selected_identity:
                    logger.info("Saving new identity:%s" % selected_identity)
                    user.selected_identity = selected_identity
                    user.save()
                    return attrs
        raise serializers.ValidationError("User is not a member of"
                                          "selected_identity: %s"
                                          % selected_identity)

    class Meta:
        model = AtmosphereUser
        exclude = ('id', 'password')