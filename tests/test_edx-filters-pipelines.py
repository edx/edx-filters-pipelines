"""
Tests for edx-filters-pipelines.py.
"""

from contextlib import contextmanager, nullcontext

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


MONITORING = 'edx_filters_pipelines.management.pipelines.monitoring'
STEP_ARGS = (
    'org.openedx.management.command.contextmanager.requested.v1',
    f'{MONITORING}.ManagementCommandMonitoringPipelineStep',
)


def test_management_command_monitoring_step_disabled(mocker):
    step = ManagementCommandMonitoringPipelineStep(*STEP_ARGS)
    command_execution = mocker.Mock()
    toggle = mocker.patch(f'{MONITORING}.ENABLE_MANAGEMENT_COMMAND_MONITORING.is_enabled', return_value=False)
    function_trace = mocker.patch(f'{MONITORING}.function_trace')

    result = step.run_filter(nullcontext(), 'migrate', 'lms')

    assert result['command_name'] == 'migrate'
    assert result['service_variant'] == 'lms'
    with result['command_contextmanager']:
        command_execution()
    toggle.assert_called_once()
    command_execution.assert_called_once()
    function_trace.assert_not_called()


def test_management_command_monitoring_step_enabled(mocker):
    step = ManagementCommandMonitoringPipelineStep(*STEP_ARGS)
    command_execution = mocker.Mock()
    mocker.patch(f'{MONITORING}.ENABLE_MANAGEMENT_COMMAND_MONITORING.is_enabled', return_value=True)
    function_trace = mocker.patch(f'{MONITORING}.function_trace', return_value=nullcontext())
    set_custom_attribute = mocker.patch(f'{MONITORING}.set_custom_attribute')

    with step.run_filter(nullcontext(), 'migrate', 'lms')['command_contextmanager']:
        command_execution()

    command_execution.assert_called_once()
    function_trace.assert_called_once_with('migrate', operation_name='django.management.command')
    set_custom_attribute.assert_any_call('management_command.service_variant', 'lms')


def test_management_command_monitoring_step_uses_configured_operation_name(mocker):
    step = ManagementCommandMonitoringPipelineStep(*STEP_ARGS, operation_name='custom.management.operation')
    command_execution = mocker.Mock()
    mocker.patch(f'{MONITORING}.ENABLE_MANAGEMENT_COMMAND_MONITORING.is_enabled', return_value=True)
    function_trace = mocker.patch(f'{MONITORING}.function_trace', return_value=nullcontext())
    mocker.patch(f'{MONITORING}.set_custom_attribute')

    with step.run_filter(nullcontext(), 'collectstatic', 'cms')['command_contextmanager']:
        command_execution()

    command_execution.assert_called_once()
    function_trace.assert_called_once_with('collectstatic', operation_name='custom.management.operation')


def test_monitor_management_command_span_wraps_the_command(mocker):
    events = []

    @contextmanager
    def fake_span(name, operation_name):
        events.append(('span_open', name, operation_name))
        try:
            yield
        finally:
            events.append(('span_close',))

    mocker.patch(f'{MONITORING}.function_trace', side_effect=fake_span)
    mocker.patch(f'{MONITORING}.set_custom_attribute')

    with monitor_management_command('migrate', 'lms'):
        events.append(('command',))

    assert events == [
        ('span_open', 'migrate', 'django.management.command'),
        ('command',),
        ('span_close',),
    ]


@pytest.mark.parametrize(
    'failing',
    ['function_trace', 'set_custom_attribute'],
)
def test_monitor_management_command_runs_command_when_monitoring_fails(mocker, failing):
    """A monitoring failure (e.g. no root span) is logged and the command still runs."""
    mocker.patch(f'{MONITORING}.function_trace', return_value=nullcontext())
    mocker.patch(f'{MONITORING}.set_custom_attribute')
    mocker.patch(f'{MONITORING}.{failing}', side_effect=AttributeError("'NoneType' object has no attribute 'resource'"))
    log = mocker.patch(f'{MONITORING}.log')
    command_execution = mocker.Mock()

    with monitor_management_command('migrate', 'lms'):
        command_execution()

    command_execution.assert_called_once()
    assert log.exception.call_count == 1


def test_monitor_management_command_propagates_command_errors(mocker):
    mocker.patch(f'{MONITORING}.function_trace', return_value=nullcontext())
    mocker.patch(f'{MONITORING}.set_custom_attribute')

    with pytest.raises(ValueError, match='command failed'):
        with monitor_management_command('migrate', 'lms'):
            raise ValueError('command failed')


@pytest.mark.parametrize(
    'run_url, expected',
    [
        ('https://github.com/edx/edx-internal/actions/runs/123', True),
        ('   ', False),
        ('', False),
    ],
)
def test_monitor_management_command_github_run_url_attribute(mocker, run_url, expected):
    mocker.patch(f'{MONITORING}.function_trace', return_value=nullcontext())
    set_custom_attribute = mocker.patch(f'{MONITORING}.set_custom_attribute')
    mocker.patch.dict('os.environ', {'EDX_MC_GITHUB_RUN_URL': run_url}, clear=False)

    with monitor_management_command('migrate', 'lms'):
        pass

    keys = [call.args[0] for call in set_custom_attribute.call_args_list]
    assert ('management_command.github_run_url' in keys) is expected
    if expected:
        set_custom_attribute.assert_any_call('management_command.github_run_url', run_url)
