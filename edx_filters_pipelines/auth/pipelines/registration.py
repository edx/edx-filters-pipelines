"""
Registration pipeline step(s) for enforcing rules during user sign-up.
"""
import logging

from openedx_filters import PipelineStep
from openedx_filters.learning.filters import StudentRegistrationRequested

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
