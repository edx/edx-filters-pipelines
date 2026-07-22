"""
Feature toggles used in the filters_pipelines app.
"""
from edx_toggles.toggles import SettingToggle, WaffleFlag

WAFFLE_NAMESPACE = 'filters_pipelines'

# .. toggle_name: filters_pipelines.enable_registration_recaptcha_validation
# .. toggle_implementation: WaffleFlag
# .. toggle_default: False
# .. toggle_description: Waffle flag to enable reCAPTCHA validation on registration
# .. toggle_use_cases: circuit_breaker
# .. toggle_creation_date: 2025-08-26
# .. toggle_target_removal_date: None because this is a long-term feature
# .. toggle_warning: When the flag is ON, recaptcha validation is enabled on registration.
ENABLE_RECAPTCHA_VALIDATION = WaffleFlag(f'{WAFFLE_NAMESPACE}.enable_registration_recaptcha_validation', __name__)

# .. toggle_name: FILTERS_PIPELINES_ENABLE_MANAGEMENT_COMMAND_MONITORING
# .. toggle_implementation: SettingToggle
# .. toggle_default: False
# .. toggle_description: Settings toggle to enable Datadog monitoring for Django management commands.
# .. toggle_use_cases: opt_in
# .. toggle_creation_date: 2026-03-26
# .. toggle_target_removal_date: None because this is a long-term feature
# .. toggle_warning: When the setting is True, management command execution is wrapped with Datadog monitoring.
ENABLE_MANAGEMENT_COMMAND_MONITORING = SettingToggle(
	'FILTERS_PIPELINES_ENABLE_MANAGEMENT_COMMAND_MONITORING',
	default=False,
)
