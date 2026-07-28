"""
Tests for edx-filters-pipelines.py.
"""

from contextlib import nullcontext

import pytest
from openedx_filters.learning.filters import StudentRegistrationRequested

from edx_filters_pipelines.auth.pipelines.registration import PreventForbiddenUsernameRegistration
from edx_filters_pipelines.management.pipelines.monitoring import (
    ManagementCommandMonitoringPipelineStep,
    monitor_management_command,
)


def test_username_blocked():
    step = PreventForbiddenUsernameRegistration(
        'org.openedx.learning.student.registration.requested.v1',
        'edx_filters_pipelines.auth.pipelines.registration.PreventForbiddenUsernameRegistration',
        forbidden_usernames=["admin", "staff"]
    )

    form_data = {"username": "admin123"}

    with pytest.raises(StudentRegistrationRequested.PreventRegistration) as exc_info:
        step.run_filter(form_data=form_data)

    assert "Usernames can't include words that could be mistaken for course roles." in str(exc_info.value)


def test_management_command_monitoring_step_disabled(mocker):
    step = ManagementCommandMonitoringPipelineStep(
        'org.openedx.platform.management.command.contextmanager.requested.v1',
        'edx_filters_pipelines.management.pipelines.monitoring.ManagementCommandMonitoringPipelineStep',
    )
    command_execution = mocker.Mock()
    toggle = mocker.patch(
        'edx_filters_pipelines.management.pipelines.monitoring.ENABLE_MANAGEMENT_COMMAND_MONITORING.is_enabled',
        return_value=False,
    )
    mocker.patch('edx_filters_pipelines.management.pipelines.monitoring.function_trace')

    result = step.run_filter(nullcontext(), 'migrate', 'lms')

    assert result['command_name'] == 'migrate'
    assert result['service_variant'] == 'lms'
    with result['command_contextmanager']:
        command_execution()
    toggle.assert_called_once()
    command_execution.assert_called_once()


def test_management_command_monitoring_step_enabled(mocker):
    step = ManagementCommandMonitoringPipelineStep(
        'org.openedx.platform.management.command.contextmanager.requested.v1',
        'edx_filters_pipelines.management.pipelines.monitoring.ManagementCommandMonitoringPipelineStep',
    )
    command_execution = mocker.Mock()
    mocker.patch(
        'edx_filters_pipelines.management.pipelines.monitoring.ENABLE_MANAGEMENT_COMMAND_MONITORING.is_enabled',
        return_value=True,
    )
    function_trace = mocker.patch(
        'edx_filters_pipelines.management.pipelines.monitoring.function_trace',
        return_value=nullcontext(),
    )
    set_transaction_name = mocker.patch(
        'edx_filters_pipelines.management.pipelines.monitoring.set_monitoring_transaction_name'
    )
    set_custom_attribute = mocker.patch(
        'edx_filters_pipelines.management.pipelines.monitoring.set_custom_attribute'
    )

    wrapped = step.run_filter(nullcontext(), 'migrate', 'lms')['command_contextmanager']

    with wrapped:
        command_execution()

    command_execution.assert_called_once()
    function_trace.assert_called_once_with('django.management.command')
    set_transaction_name.assert_called_once_with('lms.management.migrate')
    set_custom_attribute.assert_any_call('management_command.name', 'migrate')
    set_custom_attribute.assert_any_call('management_command.service_variant', 'lms')
    set_custom_attribute.assert_any_call('management_command.status', 'success')


def test_management_command_monitoring_step_uses_configured_trace_name(mocker):
    step = ManagementCommandMonitoringPipelineStep(
        'org.openedx.platform.management.command.contextmanager.requested.v1',
        'edx_filters_pipelines.management.pipelines.monitoring.ManagementCommandMonitoringPipelineStep',
        trace_name='custom.management.trace',
    )
    command_execution = mocker.Mock()
    mocker.patch(
        'edx_filters_pipelines.management.pipelines.monitoring.ENABLE_MANAGEMENT_COMMAND_MONITORING.is_enabled',
        return_value=True,
    )
    function_trace = mocker.patch(
        'edx_filters_pipelines.management.pipelines.monitoring.function_trace',
        return_value=nullcontext(),
    )
    mocker.patch('edx_filters_pipelines.management.pipelines.monitoring.set_monitoring_transaction_name')
    mocker.patch('edx_filters_pipelines.management.pipelines.monitoring.set_custom_attribute')

    with step.run_filter(nullcontext(), 'collectstatic', 'cms')['command_contextmanager']:
        command_execution()

    command_execution.assert_called_once()
    function_trace.assert_called_once_with('custom.management.trace')


@pytest.mark.parametrize(
    'raised_exception, expected_status, expected_exit_code, exception_class_recorded',
    [
        pytest.param(SystemExit(0), 'success', 0, True, id='system-exit-zero'),
        pytest.param(KeyboardInterrupt(), 'failure', None, False, id='keyboard-interrupt'),
    ],
)
def test_monitor_management_command_exception_handling(
    mocker,
    raised_exception,
    expected_status,
    expected_exit_code,
    exception_class_recorded,
):
    mocker.patch(
        'edx_filters_pipelines.management.pipelines.monitoring.function_trace',
        return_value=nullcontext(),
    )
    set_custom_attribute = mocker.patch(
        'edx_filters_pipelines.management.pipelines.monitoring.set_custom_attribute'
    )
    mocker.patch('edx_filters_pipelines.management.pipelines.monitoring.set_monitoring_transaction_name')

    with pytest.raises(type(raised_exception)) as exc_info:
        with monitor_management_command('migrate', 'lms'):
            raise raised_exception

    if expected_exit_code is not None:
        assert exc_info.value.code == expected_exit_code
        set_custom_attribute.assert_any_call('management_command.exit_code', expected_exit_code)

    if not exception_class_recorded:
        assert ('management_command.exception_class', raised_exception.__class__.__name__) not in [
            call.args for call in set_custom_attribute.call_args_list
        ]

    set_custom_attribute.assert_any_call('management_command.status', expected_status)
