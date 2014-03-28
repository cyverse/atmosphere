from atmosphere.settings import ATMOSPHERE_PRIVATE_KEYFILE

def _generate_ssh_kwargs(timeout=120):
    kwargs = {}
    kwargs.update({'ssh_key': ATMOSPHERE_PRIVATE_KEYFILE})
    kwargs.update({'timeout': timeout})
    return kwargs

