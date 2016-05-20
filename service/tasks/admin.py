from celery.decorators import task

from service.quota import set_provider_quota as spq
from threepio import celery_logger


@task(name="set_provider_quota",
      default_retry_delay=5,
      time_limit=30 * 60,  # 30minute hard-set time limit.
      max_retries=3)
def set_provider_quota(identity_uuid):
    try:
        return spq(identity_uuid)
    except Exception as exc:
        celery_logger.exception(
            "Encountered an exception trying to "
            "'set_provider_quota' for Identity UUID:%s"
            % identity_uuid)
        set_provider_quota.retry(exc=exc)
