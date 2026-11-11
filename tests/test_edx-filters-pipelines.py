"""
Tests for edx-filters-pipelines.py.
"""

from contextlib import contextmanager, nullcontext
from unittest.mock import Mock, patch

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


@patch(f'{MONITORING}.function_trace')
@patch(f'{MONITORING}.ENABLE_MANAGEMENT_COMMAND_MONITORING.is_enabled', return_value=False)
def test_management_command_monitoring_step_disabled(mock_toggle, mock_function_trace):
    step = ManagementCommandMonitoringPipelineStep(*STEP_ARGS)
    mock_command_execution = Mock()

    result = step.run_filter(nullcontext(), 'migrate', 'lms')

    assert result['command_name'] == 'migrate'
    assert result['service_variant'] == 'lms'
    with result['command_contextmanager']:
        mock_command_execution()
    mock_toggle.assert_called_once()
    mock_command_execution.assert_called_once()
    mock_function_trace.assert_not_called()


@patch(f'{MONITORING}.set_custom_attribute')
@patch(f'{MONITORING}.function_trace', return_value=nullcontext())
@patch(f'{MONITORING}.ENABLE_MANAGEMENT_COMMAND_MONITORING.is_enabled', return_value=True)
def test_management_command_monitoring_step_enabled(_mock_toggle, mock_function_trace, mock_set_custom_attribute):
    step = ManagementCommandMonitoringPipelineStep(*STEP_ARGS)
    mock_command_execution = Mock()

    with step.run_filter(nullcontext(), 'migrate', 'lms')['command_contextmanager']:
        mock_command_execution()

    mock_command_execution.assert_called_once()
    mock_function_trace.assert_called_once_with('migrate', operation_name='django.management.command')
    mock_set_custom_attribute.assert_any_call('management_command.service_variant', 'lms')


@patch(f'{MONITORING}.set_custom_attribute')
@patch(f'{MONITORING}.function_trace', return_value=nullcontext())
@patch(f'{MONITORING}.ENABLE_MANAGEMENT_COMMAND_MONITORING.is_enabled', return_value=True)
def test_management_command_monitoring_step_uses_configured_operation_name(
    _mock_toggle,
    mock_function_trace,
    _mock_set_custom_attribute,
):
    step = ManagementCommandMonitoringPipelineStep(*STEP_ARGS, operation_name='custom.management.operation')
    mock_command_execution = Mock()

    with step.run_filter(nullcontext(), 'collectstatic', 'cms')['command_contextmanager']:
        mock_command_execution()

    mock_command_execution.assert_called_once()
    mock_function_trace.assert_called_once_with('collectstatic', operation_name='custom.management.operation')


@patch(f'{MONITORING}.set_custom_attribute')
@patch(f'{MONITORING}.function_trace')
def test_monitor_management_command_span_wraps_the_command(mock_function_trace, _mock_set_custom_attribute):
    events = []

    @contextmanager
    def fake_span(name, operation_name):
        events.append(('span_open', name, operation_name))
        try:
            yield
        finally:
            events.append(('span_close',))

    mock_function_trace.side_effect = fake_span

    with monitor_management_command('migrate', 'lms'):
        events.append(('command',))

    assert events == [
        ('span_open', 'migrate', 'django.management.command'),
        ('command',),
        ('span_close',),
    ]


NO_ROOT_SPAN_ERROR = AttributeError("'NoneType' object has no attribute 'resource'")


@patch(f'{MONITORING}.log')
@patch(f'{MONITORING}.set_custom_attribute')
@patch(f'{MONITORING}.function_trace', side_effect=NO_ROOT_SPAN_ERROR)
def test_monitor_management_command_runs_command_when_span_fails(
    _mock_function_trace,
    _mock_set_custom_attribute,
    mock_log,
):
    """A failure opening the span (e.g. no root span) is logged and the command still runs."""
    mock_command_execution = Mock()

    with monitor_management_command('migrate', 'lms'):
        mock_command_execution()

    mock_command_execution.assert_called_once()
    assert mock_log.exception.call_count == 1


@patch(f'{MONITORING}.log')
@patch(f'{MONITORING}.set_custom_attribute', side_effect=NO_ROOT_SPAN_ERROR)
@patch(f'{MONITORING}.function_trace', return_value=nullcontext())
def test_monitor_management_command_runs_command_when_attribute_fails(
    _mock_function_trace,
    _mock_set_custom_attribute,
    mock_log,
):
    """A failure setting attributes is logged and the command still runs."""
    mock_command_execution = Mock()

    with monitor_management_command('migrate', 'lms'):
        mock_command_execution()

    mock_command_execution.assert_called_once()
    assert mock_log.exception.call_count == 1


@patch(f'{MONITORING}.set_custom_attribute')
@patch(f'{MONITORING}.function_trace', return_value=nullcontext())
def test_monitor_management_command_propagates_command_errors(_mock_function_trace, _mock_set_custom_attribute):
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
@patch(f'{MONITORING}.set_custom_attribute')
@patch(f'{MONITORING}.function_trace', return_value=nullcontext())
def test_monitor_management_command_github_run_url_attribute(
    _mock_function_trace,
    mock_set_custom_attribute,
    run_url,
    expected,
):
    with patch.dict('os.environ', {'EDX_MC_GITHUB_RUN_URL': run_url}):
        with monitor_management_command('migrate', 'lms'):
            pass

    keys = [call.args[0] for call in mock_set_custom_attribute.call_args_list]
    assert ('management_command.github_run_url' in keys) is expected
    if expected:
        mock_set_custom_attribute.assert_any_call('management_command.github_run_url', run_url)
