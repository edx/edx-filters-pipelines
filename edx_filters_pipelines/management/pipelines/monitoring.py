"""Pipeline steps for management command observability."""

import logging
import os
import time
from contextlib import contextmanager, nullcontext

from edx_django_utils.monitoring import function_trace, set_custom_attribute, set_monitoring_transaction_name
from openedx_filters import PipelineStep

from edx_filters_pipelines.waffle import ENABLE_MANAGEMENT_COMMAND_MONITORING

log = logging.getLogger(__name__)

DEFAULT_TRACE_NAME = 'django.management.command'

GITHUB_METADATA_ATTRIBUTE_MAP = {
    'EDX_MC_JOB_NAME': 'management_command.job_name',
    'EDX_MC_GROUP_NAME': 'management_command.group_name',
    'EDX_MC_DESCRIPTION': 'management_command.description',
    'EDX_MC_GITHUB_RUN_URL': 'management_command.github_run_url',
    'EDX_MC_GITHUB_WORKFLOW_URL': 'management_command.github_workflow_url',
    'EDX_MC_CONFIG_PATH': 'management_command.config_path',
    'EDX_MC_CONFIG_URL': 'management_command.config_url',
}


def _set_management_command_metadata_from_environment():
    """Attach workflow metadata to traces when available from automation environments."""
    metadata_attributes = {
        attribute_name: value
        for env_name, attribute_name in GITHUB_METADATA_ATTRIBUTE_MAP.items()
        if (value := os.getenv(env_name, '').strip())
    }

    for attribute_name, value in metadata_attributes.items():
        set_custom_attribute(attribute_name, value)


@contextmanager
def monitor_management_command(command_name, service_variant, trace_name=DEFAULT_TRACE_NAME):
    """
    Wrap a management command execution with Datadog monitoring metadata and a start log entry.
    """
    transaction_name = f'{service_variant}.management.{command_name}'

    set_monitoring_transaction_name(transaction_name)
    set_custom_attribute('management_command.name', command_name)
    set_custom_attribute('management_command.service_variant', service_variant)
    set_custom_attribute('management_command.transaction_name', transaction_name)
    _set_management_command_metadata_from_environment()
    log.info(
        'Starting management command: %s service_variant=%s transaction_name=%s',
        command_name,
        service_variant,
        transaction_name,
    )

    start_time = time.monotonic()
    status = 'failure'

    try:
        with function_trace(trace_name):
            yield
        status = 'success'
    except SystemExit as exc:
        set_custom_attribute('management_command.exception_class', exc.__class__.__name__)
        set_custom_attribute('management_command.exit_code', exc.code)
        set_custom_attribute('management_command.exception_message', str(exc))
        if exc.code in (0, None):
            status = 'success'
        else:
            log.exception(
                'Management command failed: %s service_variant=%s transaction_name=%s exit_code=%s error=%s',
                command_name,
                service_variant,
                transaction_name,
                exc.code,
                exc,
            )
        raise
    except Exception as exc:
        set_custom_attribute('management_command.exception_class', exc.__class__.__name__)
        set_custom_attribute('management_command.exception_message', str(exc))
        log.exception(
            'Management command failed: %s service_variant=%s transaction_name=%s exception_class=%s error=%s',
            command_name,
            service_variant,
            transaction_name,
            exc.__class__.__name__,
            exc,
        )
        raise
    finally:
        duration = time.monotonic() - start_time
        set_custom_attribute('management_command.status', status)
        set_custom_attribute('management_command.duration_seconds', duration)
        log.info(
            'Finished management command: %s service_variant=%s transaction_name=%s status=%s duration_seconds=%s',
            command_name,
            service_variant,
            transaction_name,
            status,
            duration,
        )


class ManagementCommandMonitoringPipelineStep(PipelineStep):
    """
    Add Datadog monitoring around Django management command execution.
    """

    def run_filter(self, command_contextmanager, command_name, service_variant):  # pylint: disable=arguments-differ
        """
        Return a wrapped context manager that applies monitoring when enabled.
        """
        trace_name = self.extra_config.get('trace_name', DEFAULT_TRACE_NAME)

        @contextmanager
        def wrapped_contextmanager():
            monitor_contextmanager = nullcontext()

            try:
                if ENABLE_MANAGEMENT_COMMAND_MONITORING.is_enabled():
                    monitor_contextmanager = monitor_management_command(command_name, service_variant, trace_name)
            except Exception:  # pylint: disable=broad-except
                log.exception(
                    'Failed to initialize management command monitoring for %s; continuing without monitoring.',
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
