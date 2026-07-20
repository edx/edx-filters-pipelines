"""Pipeline steps for management command observability."""

import logging
import time
from contextlib import contextmanager, nullcontext

from edx_django_utils.monitoring import function_trace, set_custom_attribute, set_monitoring_transaction_name
from openedx_filters import PipelineStep

from edx_filters_pipelines.waffle import ENABLE_MANAGEMENT_COMMAND_MONITORING

log = logging.getLogger(__name__)

DEFAULT_TRACE_NAME = 'django.management.command'


@contextmanager
def monitor_management_command(command_name, service_variant, trace_name=DEFAULT_TRACE_NAME):
    """
    Wrap a management command execution with Datadog monitoring metadata.
    """
    transaction_name = f'{service_variant}.management.{command_name}'

    set_monitoring_transaction_name(transaction_name)
    set_custom_attribute('management_command.name', command_name)
    set_custom_attribute('management_command.service_variant', service_variant)
    set_custom_attribute('management_command.transaction_name', transaction_name)

    start_time = time.monotonic()
    status = 'failure'

    try:
        with function_trace(trace_name):
            yield
        status = 'success'
    except BaseException as exc:
        set_custom_attribute('management_command.exception_class', exc.__class__.__name__)
        if isinstance(exc, SystemExit):
            set_custom_attribute('management_command.exit_code', exc.code)
        raise
    finally:
        set_custom_attribute('management_command.status', status)
        set_custom_attribute('management_command.duration_seconds', time.monotonic() - start_time)


class ManagementCommandMonitoringPipelineStep(PipelineStep):
    """
    Add Datadog monitoring around Django management command execution.
    """

    def run_filter(self, command_name, service_variant, command_runner):  # pylint: disable=arguments-differ
        """
        Return a wrapped command runner that applies monitoring when enabled.
        """
        trace_name = self.extra_config.get('trace_name', DEFAULT_TRACE_NAME)

        def wrapped_runner():
            monitor_context = nullcontext()

            try:
                if ENABLE_MANAGEMENT_COMMAND_MONITORING.is_enabled():
                    monitor_context = monitor_management_command(command_name, service_variant, trace_name)
            except Exception:  # pylint: disable=broad-except
                log.exception(
                    'Failed to initialize management command monitoring for %s; continuing without monitoring.',
                    command_name,
                )

            with monitor_context:
                return command_runner()

        return {
            'command_name': command_name,
            'service_variant': service_variant,
            'command_runner': wrapped_runner,
        }
