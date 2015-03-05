from celery.decorators import task

from core.models import QuotaRequest
from core.models.status_type import get_status_type

from service.quota import set_provider_quota as spq


@task(name="set_provider_quota",
      default_retry_delay=5,
      time_limit=30*60,  # 30minute hard-set time limit.
      max_retries=3)
def set_provider_quota(identity_uuid):
    try:
        spq(identity_uuid)
    except Exception as exc:
        set_provider_quota.retry(exc=exc)


@task(name='set_quota_request_failed')
def set_quota_request_failed(err, identifier):
    """
    Set the quota request as failed if
    Marks the quota request ask
    """
    request = QuotaRequest.objects.get(uuid=identifier)
    request.status = get_status_type(status="failed")
    request.save()
