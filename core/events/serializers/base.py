from rest_framework import serializers


# noinspection PyAbstractClass
class EventSerializer(serializers.Serializer):
    """
    EventSerializers take _anything they need_ as Input
    EventSerializers are responsible for validation
    EventSerializers will save events to the EventTable
    """
    def save(self):
        """
        On save:
          - The 'entity_id' and 'payload' of the event should be properly formatted and structured
          - EventSerializers should save and return the event:
            ```
                event = EventTable.create_event(
                    name="...",
                    entity_id=entity_id,
                    payload=event_payload)
                return event
            ```
        """
        raise NotImplemented("Implement this in the sub-class")
