"""Pipeline steps for management command observability."""

import logging
import os
from contextlib import ExitStack, contextmanager, nullcontext

from edx_django_utils.monitoring import function_trace, set_custom_attribute
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
    Opens a span with the command name as the resource_name.
    """
    resource_name = command_name

    with ExitStack() as stack:
        try:
            stack.enter_context(
                # opens the management command span
                function_trace(resource_name, operation_name=operation_name)
            )
            set_custom_attribute('management_command.service_variant', service_variant)

            github_run_url = os.getenv('EDX_MC_GITHUB_RUN_URL', '').strip()
            if github_run_url:
                set_custom_attribute('management_command.github_run_url', github_run_url)
        except Exception:  # pylint: disable=broad-except
            log.exception(
                'Failed to set up monitoring for management command %s; continuing without it.',
                command_name,
            )

        yield


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
