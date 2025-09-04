"""
Registration pipeline step(s) for enforcing rules during user sign-up.
"""
import logging

from openedx_filters import PipelineStep
from openedx_filters.learning.filters import StudentRegistrationRequested

from edx_filters_pipelines.auth.utils import verify_recaptcha_token
from edx_filters_pipelines.waffle import ENABLE_RECAPTCHA_VALIDATION

logger = logging.getLogger(__name__)


class PreventForbiddenUsernameRegistration(PipelineStep):
    """
    A filter pipeline step that prevents user registration if the chosen username contains
    any forbidden substrings.

    This filter should be configured via the `OPEN_EDX_FILTERS_CONFIG` setting in edx-platform
    as follows:

        OPEN_EDX_FILTERS_CONFIG = {
            "org.openedx.learning.student.registration.requested.v1": {
                "pipeline": [
                    "edx_filters_pipelines.auth.pipelines.registration.PreventForbiddenUsernameRegistration"
                ],
                "forbidden_usernames": ['admin', 'test', 'staff'],
                "fail_silently": False
            }
        }

    """

    def run_filter(self, **kwargs):
        """
        Executes the filter logic to block registration if the username contains
        any forbidden substrings defined in the configuration.

        Raises:
            StudentRegistrationRequested.PreventRegistration: If the username is considered invalid.
        """
        form_data = kwargs.get("form_data", {})
        username = str(form_data.get("username", "")).strip()
        forbidden_usernames = self.extra_config.get("forbidden_usernames", [])

        forbidden_match = next((f for f in forbidden_usernames if f.lower() in username.lower()), None)
        if forbidden_match:
            logger.info(
                f"Registration blocked: username '{username}' contains forbidden term '{forbidden_match}'."
            )
            raise StudentRegistrationRequested.PreventRegistration(
                message=(
                    "Usernames can't include words that could be mistaken for course roles. "
                    "Please choose a different username."
                ),
                status_code=403,
                error_code='forbidden-username'
            )
        return form_data


class VerifyReCaptchaToken(PipelineStep):
    """
    A filter pipeline step that verifies the reCAPTCHA token provided during registration.

    This filter should be configured via the `OPEN_EDX_FILTERS_CONFIG` setting in edx-platform
    as follows:

        OPEN_EDX_FILTERS_CONFIG = {
            "org.openedx.learning.student.registration.requested.v1": {
                "pipeline": [
                    "edx_filters_pipelines.auth.pipelines.registration.VerifyReCaptchaToken"
                ],
                "fail_silently": False
            }
        }

    """

    def run_filter(self, **kwargs):
        """
        Executes the filter logic to verify the reCAPTCHA token.

        Raises:
            StudentRegistrationRequested.PreventRegistration: If the reCAPTCHA verification fails.
        """
        form_data = kwargs.get("form_data", {})
        if not ENABLE_RECAPTCHA_VALIDATION.is_enabled():
            return form_data
        if verify_recaptcha_token(form_data.get("recaptcha_token", "")):
            logger.info("reCAPTCHA token verification passed.")
        else:
            logger.error("reCAPTCHA token verification failed.")
            raise StudentRegistrationRequested.PreventRegistration(
                message="reCAPTCHA verification failed. Please try again.",
                status_code=403,
                error_code='recaptcha-verification-failed'
            )
        return form_data
