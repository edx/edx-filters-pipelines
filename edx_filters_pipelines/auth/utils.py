"""
reCAPTCHA verification utility using Google Cloud SDK.
"""

import logging
from typing import Optional

from crum import get_current_request
from django.conf import settings
from google.cloud import recaptchaenterprise_v1
from google.api_core import exceptions as google_exceptions
from google.api_core.client_options import ClientOptions

IGNORE_VALIDATION_ON_ERROR = True


def get_platform_from_request():
    """
    get Mobile-Platform-Identifier header value from request
    Default to 'web' if header is not present
    """
    request = get_current_request()
    return request.headers.get('Mobile-Platform-Identifier', 'web') if request else 'web'


def get_captcha_site_key_by_platform(platform: str) -> Optional[str]:
    """
     Get reCAPTCHA site key based on the platform.
    """
    return settings.RECAPTCHA_SITE_KEYS.get(platform, None)


class RecaptchaVerifier:
    """Handle reCAPTCHA verification using Google Cloud SDK."""

    def __init__(self, project_id: str, api_key: Optional[str]):
        """
        Initialize the reCAPTCHA verifier.

        Args:
            project_id: Google Cloud project ID
            api_key: Optional API key for authentication
        """
        self.project_id = project_id

        # Use API key authentication
        client_options = ClientOptions(api_key=api_key)
        self.client = recaptchaenterprise_v1.RecaptchaEnterpriseServiceClient(
            client_options=client_options
        )

    def verify_token(self, token: str, site_key: str) -> bool:
        """
        Verify reCAPTCHA token validity.

        Args:
            token: The reCAPTCHA token to verify
            site_key: The site key for the reCAPTCHA

        Returns:
            bool: True if token is valid
        """
        if not site_key or not site_key.strip():
            logging.error("reCAPTCHA Site key is required")
            return IGNORE_VALIDATION_ON_ERROR

        if not token or not token.strip():
            logging.warning("Empty reCAPTCHA token provided")
            return False

        try:
            # Create assessment request
            event = recaptchaenterprise_v1.Event({
                "token": token,
                "site_key": site_key,
            })

            assessment = recaptchaenterprise_v1.Assessment({"event": event})
            project_name = f"projects/{self.project_id}"

            request = recaptchaenterprise_v1.CreateAssessmentRequest({
                "parent": project_name,
                "assessment": assessment,
            })

            response = self.client.create_assessment(request=request)

            # Check token validity
            if response.token_properties.valid:
                logging.info("reCAPTCHA token verification successful")
                return True
            else:
                invalid_reason = response.token_properties.invalid_reason
                logging.warning(f"reCAPTCHA token invalid: {invalid_reason}")
                return False

        except google_exceptions.GoogleAPICallError as e:
            logging.error(f"Google API error during reCAPTCHA verification: {e}")
            return IGNORE_VALIDATION_ON_ERROR

        except google_exceptions.RetryError as e:
            logging.error(f"Retry limit exceeded for reCAPTCHA verification: {e}")
            return IGNORE_VALIDATION_ON_ERROR

        except Exception as e:  # pylint: disable=broad-except
            logging.error(f"Unexpected error during reCAPTCHA verification: {e}", exc_info=True)
            return IGNORE_VALIDATION_ON_ERROR


def create_recaptcha_verifier() -> Optional[RecaptchaVerifier]:
    """
    Create a new reCAPTCHA verifier instance.

    Returns:
        RecaptchaVerifier: Configured verifier instance, or None if settings missing

    """
    if not hasattr(settings, 'RECAPTCHA_PROJECT_ID') or not settings.RECAPTCHA_PROJECT_ID:
        logging.warning("RECAPTCHA_PROJECT_ID setting not configured - skipping reCAPTCHA verification")
        return None

    api_key = getattr(settings, 'RECAPTCHA_PRIVATE_KEY', None)
    return RecaptchaVerifier(settings.RECAPTCHA_PROJECT_ID, api_key)


def verify_recaptcha_token(token: str, verifier: Optional[RecaptchaVerifier] = None) -> bool:
    """
    Verify reCAPTCHA token using Google Cloud SDK.

    Args:
        token: The reCAPTCHA token to verify
        verifier: Optional verifier instance. If None, creates a new one.

    Returns:
        bool: True if token is valid or reCAPTCHA is not configured, False otherwise
    """
    try:
        # Check if reCAPTCHA site keys are configured
        if is_sso_registration():
            logging.info("SSO registration detected - skipping reCAPTCHA verification")
            return True
        if not hasattr(settings, 'RECAPTCHA_SITE_KEYS') or not settings.RECAPTCHA_SITE_KEYS:
            logging.warning("RECAPTCHA_SITE_KEYS not configured - skipping reCAPTCHA verification")
            return True

        site_key = get_captcha_site_key_by_platform(get_platform_from_request())
        if not site_key:
            logging.warning("Could not determine site key for current platform - skipping reCAPTCHA verification")
            return True

        if verifier is None:
            verifier = create_recaptcha_verifier()

        # If verifier creation failed due to missing settings, skip verification
        if verifier is None:
            return True

        return verifier.verify_token(token, site_key)

    except Exception as e:  # pylint: disable=broad-except
        logging.error(f"Error during reCAPTCHA verification: {e}", exc_info=True)
        return True  # Return True on errors to not block users


def is_sso_registration() -> bool:
    """
    Check if the current registration request is part of an SSO pipeline.
    """
    request = get_current_request()
    # Check for both 'partial_pipeline_token' and 'partial_pipeline_token_' to support possible
    # variations in session key naming (e.g., legacy code, different pipeline implementations).
    if request is None:
        return False
    return request.session.get('partial_pipeline_token') or request.session.get('partial_pipeline_token_')
