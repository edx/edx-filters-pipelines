"""
waffle flags used in the filters_pipelines app.
"""
from edx_toggles.toggles import WaffleFlag

WAFFLE_NAMESPACE = 'filters_pipelines'

# .. toggle_name: filters_pipelines.enable_registration_recaptcha_validation
# .. toggle_implementation: WaffleFlag
# .. toggle_default: False
# .. toggle_description: Waffle flag to enable the Notifications feature
# .. toggle_use_cases: temporary
# .. toggle_creation_date: 2025-08-26
# .. toggle_target_removal_date: 202026-01-01
# .. toggle_warning: When the flag is ON, recaptcha validation is enabled on registration.
ENABLE_RECAPTCHA_VALIDATION = WaffleFlag(f'{WAFFLE_NAMESPACE}.enable_registration_recaptcha_validation', __name__)
