from celery.decorators import task

from service.quota import set_provider_quota as spq


@task(name="set_provider_quota",
      default_retry_delay=32,
      time_limit=30*60,  # 30minute hard-set time limit.
      max_retries=3)
def set_provider_quota(identity_uuid):
    try:
        spq(identity_uuid)
    except Exception as exc:
        set_provider_quota.retry(exc=exc)
