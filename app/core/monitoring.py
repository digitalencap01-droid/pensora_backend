import logging

from app.core.config import settings


logger = logging.getLogger(__name__)

_enabled = False

if settings.sentry_dsn:
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        send_default_pii=False,
        traces_sample_rate=(
            0.0 if settings.debug else 0.1
        ),
    )
    _enabled = True


def capture_exception(
    exc: BaseException,
    **context: object,
) -> None:
    if not _enabled:
        return

    import sentry_sdk

    with sentry_sdk.push_scope() as scope:
        for key, value in context.items():
            scope.set_context(
                key,
                {"value": value},
            )
        sentry_sdk.capture_exception(exc)
