"""Pipeline steps for management command observability."""

import logging
import os
import time
from contextlib import contextmanager, nullcontext

from edx_django_utils.monitoring import (
    function_trace,
    set_custom_attribute,
    set_monitoring_transaction_name,
)
from openedx_filters import PipelineStep

from edx_filters_pipelines.waffle import ENABLE_MANAGEMENT_COMMAND_MONITORING

log = logging.getLogger(__name__)

DEFAULT_OPERATION_NAME = 'django.management.command'


@contextmanager
def monitor_management_command(
    command_name,
    service_variant,
    operation_name=DEFAULT_OPERATION_NAME,
):
    """
    Wrap a management command execution with monitoring metadata and logging.

    The operation name identifies the type of operation, while the resource
    name identifies the specific management command being executed.
    """
    resource_name = f'{service_variant}.management.{command_name}'

    set_monitoring_transaction_name(resource_name)
    set_custom_attribute('management_command.name', command_name)
    set_custom_attribute('management_command.service_variant', service_variant)

    github_run_url = os.getenv('EDX_MC_GITHUB_RUN_URL', '').strip()
    if github_run_url:
        set_custom_attribute('management_command.github_run_url', github_run_url)

    log.info(
        'Starting management command: %s service_variant=%s '
        'operation_name=%s resource_name=%s',
        command_name,
        service_variant,
        operation_name,
        resource_name,
    )

    start_time = time.monotonic()
    status = 'failure'

    try:
        with function_trace(resource_name, operation_name=operation_name):
            yield

        status = 'success'

    except SystemExit as exc:
        if exc.code in (0, None):
            status = 'success'
        else:
            set_custom_attribute('management_command.exception_class', exc.__class__.__name__)
            set_custom_attribute('management_command.exit_code', exc.code)
            set_custom_attribute('management_command.exception_message', str(exc))
            log.exception(
                'Management command failed: %s service_variant=%s '
                'operation_name=%s resource_name=%s exit_code=%s error=%s',
                command_name,
                service_variant,
                operation_name,
                resource_name,
                exc.code,
                exc,
            )
        raise

    except Exception as exc:
        set_custom_attribute('management_command.exception_class', exc.__class__.__name__)
        set_custom_attribute('management_command.exception_message', str(exc))
        log.exception(
            'Management command failed: %s service_variant=%s '
            'operation_name=%s resource_name=%s exception_class=%s error=%s',
            command_name,
            service_variant,
            operation_name,
            resource_name,
            exc.__class__.__name__,
            exc,
        )
        raise

    finally:
        duration = time.monotonic() - start_time
        set_custom_attribute('management_command.status', status)
        set_custom_attribute('management_command.duration_seconds', duration)
        log.info(
            'Finished management command: %s service_variant=%s '
            'operation_name=%s resource_name=%s status=%s duration_seconds=%s',
            command_name,
            service_variant,
            operation_name,
            resource_name,
            status,
            duration,
        )


class ManagementCommandMonitoringPipelineStep(PipelineStep):
    """
    Add monitoring around Django management command execution.
    """

    def run_filter(
        self,
        command_contextmanager,
        command_name,
        service_variant,
    ):  # pylint: disable=arguments-differ
        """
        Return a wrapped context manager that applies monitoring when enabled.
        """
        operation_name = self.extra_config.get('operation_name', DEFAULT_OPERATION_NAME)

        @contextmanager
        def wrapped_contextmanager():
            monitor_contextmanager = nullcontext()

            try:
                if ENABLE_MANAGEMENT_COMMAND_MONITORING.is_enabled():
                    monitor_contextmanager = monitor_management_command(
                        command_name,
                        service_variant,
                        operation_name,
                    )
            except Exception:  # pylint: disable=broad-except
                log.exception(
                    'Failed to initialize management command monitoring '
                    'for %s; continuing without monitoring.',
                    command_name,
                )

            with monitor_contextmanager:
                with command_contextmanager:
                    yield

        return {
            'command_contextmanager': wrapped_contextmanager(),
            'command_name': command_name,
            'service_variant': service_variant,
        }
