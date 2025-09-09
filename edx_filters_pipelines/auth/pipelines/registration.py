"""
Registration pipeline step(s) for enforcing rules during user sign-up.
"""
import logging
from typing import Any, Dict

from openedx_filters import PipelineStep
from openedx_filters.learning.filters import StudentRegistrationRequested

logger = logging.getLogger(__name__)


class PreventForbiddenUsernameRegistration(PipelineStep):
    """
    Prevent user registration if the username contains forbidden substrings.

    This filter pipeline step prevents user registration if the chosen username
    contains any forbidden substrings.

    This filter should be configured via the `OPEN_EDX_FILTERS_CONFIG` setting
    in edx-platform as follows:

        OPEN_EDX_FILTERS_CONFIG = {
            "org.openedx.learning.student.registration.requested.v1": {
                "pipeline": [
                    "edx_filters_pipelines.auth.pipelines.registration."
                    "PreventForbiddenUsernameRegistration"
                ],
                "forbidden_usernames": ['admin', 'test', 'staff'],
                "fail_silently": False
            }
        }
    """

    def run_filter(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Execute the filter logic to block registration for forbidden usernames.

        Block registration if the username contains any forbidden substrings
        defined in the configuration.

        Args:
            **kwargs: Arbitrary keyword arguments. Expected to contain
                'form_data' with user registration information.

        Returns:
            Dict[str, Any]: The form data if username is allowed.

        Raises:
            StudentRegistrationRequested.PreventRegistration: If the username
                is considered invalid.
        """
        form_data = kwargs.get("form_data", {})
        username = str(form_data.get("username", "")).strip()
        forbidden_usernames = self.extra_config.get("forbidden_usernames", [])

        # Ensure forbidden_usernames is a list for security
        if not isinstance(forbidden_usernames, list):
            logger.warning(
                "forbidden_usernames configuration must be a list, got %s",
                type(forbidden_usernames).__name__
            )
            forbidden_usernames = []

        # Skip checking if username is empty or forbidden list is empty
        if not username or not forbidden_usernames:
            return form_data

        # Check for forbidden terms (case-insensitive)
        username_lower = username.lower()
        forbidden_match = next(
            (term for term in forbidden_usernames
             if isinstance(term, str) and term.lower() in username_lower),
            None
        )
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
