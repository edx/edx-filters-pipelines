"""
Tests for edx-filters-pipelines.py.
"""

from contextlib import nullcontext

import pytest
from openedx_filters.learning.filters import StudentRegistrationRequested

from edx_filters_pipelines.auth.pipelines.registration import PreventForbiddenUsernameRegistration
from edx_filters_pipelines.management.pipelines.monitoring import (
    GITHUB_METADATA_ATTRIBUTE_MAP,
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
    mocker.patch(
        'edx_filters_pipelines.management.pipelines.monitoring.time.monotonic',
        side_effect=[10.0, 15.0],
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
    log = mocker.patch('edx_filters_pipelines.management.pipelines.monitoring.log')

    wrapped = step.run_filter(nullcontext(), 'migrate', 'lms')['command_contextmanager']

    with wrapped:
        command_execution()

    command_execution.assert_called_once()
    function_trace.assert_called_once_with('django.management.command')
    set_transaction_name.assert_called_once_with('lms.management.migrate')
    set_custom_attribute.assert_any_call('management_command.name', 'migrate')
    set_custom_attribute.assert_any_call('management_command.service_variant', 'lms')
    set_custom_attribute.assert_any_call('management_command.duration_seconds', 5.0)
    set_custom_attribute.assert_any_call('management_command.status', 'success')
    log.info.assert_any_call(
        'Starting management command: %s service_variant=%s transaction_name=%s',
        'migrate',
        'lms',
        'lms.management.migrate',
    )
    log.info.assert_any_call(
        'Finished management command: %s service_variant=%s transaction_name=%s status=%s duration_seconds=%s',
        'migrate',
        'lms',
        'lms.management.migrate',
        'success',
        5.0,
    )


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


def test_monitor_management_command_logs_failure(mocker):
    mocker.patch(
        'edx_filters_pipelines.management.pipelines.monitoring.time.monotonic',
        side_effect=[10.0, 15.0],
    )
    mocker.patch(
        'edx_filters_pipelines.management.pipelines.monitoring.function_trace',
        return_value=nullcontext(),
    )
    set_custom_attribute = mocker.patch(
        'edx_filters_pipelines.management.pipelines.monitoring.set_custom_attribute'
    )
    log = mocker.patch('edx_filters_pipelines.management.pipelines.monitoring.log')
    mocker.patch('edx_filters_pipelines.management.pipelines.monitoring.set_monitoring_transaction_name')

    with pytest.raises(RuntimeError):
        with monitor_management_command('migrate', 'lms'):
            raise RuntimeError('boom')

    log.info.assert_any_call(
        'Starting management command: %s service_variant=%s transaction_name=%s',
        'migrate',
        'lms',
        'lms.management.migrate',
    )
    assert log.exception.call_count == 1
    assert log.exception.call_args.args[:5] == (
        'Management command failed: %s service_variant=%s transaction_name=%s exception_class=%s error=%s',
        'migrate',
        'lms',
        'lms.management.migrate',
        'RuntimeError',
    )
    assert str(log.exception.call_args.args[5]) == 'boom'
    set_custom_attribute.assert_any_call('management_command.status', 'failure')
    set_custom_attribute.assert_any_call('management_command.duration_seconds', 5.0)
    set_custom_attribute.assert_any_call('management_command.exception_message', 'boom')
    log.info.assert_any_call(
        'Finished management command: %s service_variant=%s transaction_name=%s status=%s duration_seconds=%s',
        'migrate',
        'lms',
        'lms.management.migrate',
        'failure',
        5.0,
    )


def test_monitor_management_command_sets_github_metadata_attributes(mocker):
    mocker.patch(
        'edx_filters_pipelines.management.pipelines.monitoring.function_trace',
        return_value=nullcontext(),
    )
    set_custom_attribute = mocker.patch(
        'edx_filters_pipelines.management.pipelines.monitoring.set_custom_attribute'
    )
    mocker.patch('edx_filters_pipelines.management.pipelines.monitoring.set_monitoring_transaction_name')
    mocker.patch.dict(
        'os.environ',
        {
            'EDX_MC_JOB_NAME': 'notify_credentials',
            'EDX_MC_GROUP_NAME': 'grading',
            'EDX_MC_GITHUB_RUN_URL': 'https://github.com/edx/edx-internal/actions/runs/123',
            'EDX_MC_CONFIG_PATH': 'argocd/applications/edxapp-lms/management-commands/stage.yml',
        },
        clear=False,
    )

    with monitor_management_command('migrate', 'lms'):
        pass

    set_custom_attribute.assert_any_call('management_command.job_name', 'notify_credentials')
    set_custom_attribute.assert_any_call('management_command.group_name', 'grading')
    set_custom_attribute.assert_any_call(
        'management_command.github_run_url',
        'https://github.com/edx/edx-internal/actions/runs/123',
    )
    set_custom_attribute.assert_any_call(
        'management_command.config_path',
        'argocd/applications/edxapp-lms/management-commands/stage.yml',
    )


def test_monitor_management_command_metadata_mapping_uses_all_defined_keys(mocker):
    mocker.patch(
        'edx_filters_pipelines.management.pipelines.monitoring.function_trace',
        return_value=nullcontext(),
    )
    set_custom_attribute = mocker.patch(
        'edx_filters_pipelines.management.pipelines.monitoring.set_custom_attribute'
    )
    mocker.patch('edx_filters_pipelines.management.pipelines.monitoring.set_monitoring_transaction_name')

    metadata_env = {
        env_name: f'value-for-{env_name.lower()}'
        for env_name in GITHUB_METADATA_ATTRIBUTE_MAP
    }
    mocker.patch.dict('os.environ', metadata_env, clear=False)

    with monitor_management_command('migrate', 'lms'):
        pass

    for env_name, attribute_name in GITHUB_METADATA_ATTRIBUTE_MAP.items():
        set_custom_attribute.assert_any_call(attribute_name, metadata_env[env_name])


def test_monitor_management_command_metadata_mapping_ignores_blank_values(mocker):
    mocker.patch(
        'edx_filters_pipelines.management.pipelines.monitoring.function_trace',
        return_value=nullcontext(),
    )
    set_custom_attribute = mocker.patch(
        'edx_filters_pipelines.management.pipelines.monitoring.set_custom_attribute'
    )
    mocker.patch('edx_filters_pipelines.management.pipelines.monitoring.set_monitoring_transaction_name')

    metadata_env = {
        env_name: '   '
        for env_name in GITHUB_METADATA_ATTRIBUTE_MAP
    }
    mocker.patch.dict('os.environ', metadata_env, clear=False)

    with monitor_management_command('migrate', 'lms'):
        pass

    metadata_calls = [
        call.args[0]
        for call in set_custom_attribute.call_args_list
        if call.args[0].startswith('management_command.')
    ]
    for attribute_name in GITHUB_METADATA_ATTRIBUTE_MAP.values():
        assert attribute_name not in metadata_calls


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

    if exception_class_recorded:
        set_custom_attribute.assert_any_call('management_command.exception_message', str(raised_exception))

    if not exception_class_recorded:
        assert ('management_command.exception_class', raised_exception.__class__.__name__) not in [
            call.args for call in set_custom_attribute.call_args_list
        ]

    set_custom_attribute.assert_any_call('management_command.status', expected_status)
