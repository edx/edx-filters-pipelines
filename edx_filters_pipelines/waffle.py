"""
waffle flags used in the filters_pipelines app.
"""
from edx_toggles.toggles import WaffleFlag

WAFFLE_NAMESPACE = 'filters_pipelines'

# .. toggle_name: filters_pipelines.enable_registration_recaptcha_validation
# .. toggle_implementation: WaffleFlag
# .. toggle_default: False
# .. toggle_description: Waffle flag to enable reCAPTCHA validation on registration
# .. toggle_use_cases: long_term
# .. toggle_creation_date: 2025-08-26
# .. toggle_target_removal_date: None because this is a long-term feature
# .. toggle_warning: When the flag is ON, recaptcha validation is enabled on registration.
ENABLE_RECAPTCHA_VALIDATION = WaffleFlag(f'{WAFFLE_NAMESPACE}.enable_registration_recaptcha_validation', __name__)
