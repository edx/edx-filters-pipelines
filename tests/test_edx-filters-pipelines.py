"""
Tests for edx-filters-pipelines.py.
"""

from contextlib import nullcontext

import pytest
from openedx_filters.learning.filters import StudentRegistrationRequested

from edx_filters_pipelines.auth.pipelines.registration import PreventForbiddenUsernameRegistration
from edx_filters_pipelines.management.pipelines.monitoring import ManagementCommandMonitoringPipelineStep


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
        'org.openedx.platform.management.command.execute.requested.v1',
        'edx_filters_pipelines.management.pipelines.monitoring.ManagementCommandMonitoringPipelineStep',
    )
    command_runner = mocker.Mock(return_value='ok')
    toggle = mocker.patch(
        'edx_filters_pipelines.management.pipelines.monitoring.ENABLE_MANAGEMENT_COMMAND_MONITORING.is_enabled',
        return_value=False,
    )
    mocker.patch('edx_filters_pipelines.management.pipelines.monitoring.function_trace')

    result = step.run_filter('migrate', 'lms', command_runner)

    assert result['command_name'] == 'migrate'
    assert result['service_variant'] == 'lms'
    assert result['command_runner']() == 'ok'
    toggle.assert_called_once()
    command_runner.assert_called_once()


def test_management_command_monitoring_step_enabled(mocker):
    step = ManagementCommandMonitoringPipelineStep(
        'org.openedx.platform.management.command.execute.requested.v1',
        'edx_filters_pipelines.management.pipelines.monitoring.ManagementCommandMonitoringPipelineStep',
    )
    command_runner = mocker.Mock(return_value='ok')
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

    wrapped = step.run_filter('migrate', 'lms', command_runner)['command_runner']

    assert wrapped() == 'ok'
    function_trace.assert_called_once_with('django.management.command')
    set_transaction_name.assert_called_once_with('lms.management.migrate')
    set_custom_attribute.assert_any_call('management_command.name', 'migrate')
    set_custom_attribute.assert_any_call('management_command.service_variant', 'lms')
    set_custom_attribute.assert_any_call('management_command.status', 'success')


def test_management_command_monitoring_step_uses_configured_trace_name(mocker):
    step = ManagementCommandMonitoringPipelineStep(
        'org.openedx.platform.management.command.execute.requested.v1',
        'edx_filters_pipelines.management.pipelines.monitoring.ManagementCommandMonitoringPipelineStep',
        trace_name='custom.management.trace',
    )
    command_runner = mocker.Mock(return_value=None)
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

    step.run_filter('collectstatic', 'cms', command_runner)['command_runner']()

    function_trace.assert_called_once_with('custom.management.trace')
