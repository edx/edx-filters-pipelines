"""
Tests for edx-filters-pipelines.py.
"""

import pytest
from openedx_filters.learning.filters import StudentRegistrationRequested

from edx_filters_pipelines.auth.pipelines.registration import PreventForbiddenUsernameRegistration


def test_username_blocked():
    """Test that a username containing forbidden terms is blocked."""
    step = PreventForbiddenUsernameRegistration(
        'org.openedx.learning.student.registration.requested.v1',
        'edx_filters_pipelines.auth.pipelines.registration.PreventForbiddenUsernameRegistration',
        forbidden_usernames=["admin", "staff"]
    )

    form_data = {"username": "admin123"}

    with pytest.raises(StudentRegistrationRequested.PreventRegistration) as exc_info:
        step.run_filter(form_data=form_data)

    assert "Usernames can't include words that could be mistaken for course roles." in str(exc_info.value)


def test_username_allowed():
    """Test that a username without forbidden terms is allowed."""
    step = PreventForbiddenUsernameRegistration(
        'org.openedx.learning.student.registration.requested.v1',
        'edx_filters_pipelines.auth.pipelines.registration.PreventForbiddenUsernameRegistration',
        forbidden_usernames=["admin", "staff"]
    )

    form_data = {"username": "student123"}
    result = step.run_filter(form_data=form_data)

    assert result == form_data


def test_case_insensitive_blocking():
    """Test that forbidden username checking is case insensitive."""
    step = PreventForbiddenUsernameRegistration(
        'org.openedx.learning.student.registration.requested.v1',
        'edx_filters_pipelines.auth.pipelines.registration.PreventForbiddenUsernameRegistration',
        forbidden_usernames=["admin", "staff"]
    )

    form_data = {"username": "ADMIN123"}

    with pytest.raises(StudentRegistrationRequested.PreventRegistration) as exc_info:
        step.run_filter(form_data=form_data)

    assert "Usernames can't include words that could be mistaken for course roles." in str(exc_info.value)


def test_empty_forbidden_list():
    """Test behavior when no forbidden usernames are configured."""
    step = PreventForbiddenUsernameRegistration(
        'org.openedx.learning.student.registration.requested.v1',
        'edx_filters_pipelines.auth.pipelines.registration.PreventForbiddenUsernameRegistration',
        forbidden_usernames=[]
    )

    form_data = {"username": "admin123"}
    result = step.run_filter(form_data=form_data)

    assert result == form_data


def test_missing_username():
    """Test behavior when username is missing from form data."""
    step = PreventForbiddenUsernameRegistration(
        'org.openedx.learning.student.registration.requested.v1',
        'edx_filters_pipelines.auth.pipelines.registration.PreventForbiddenUsernameRegistration',
        forbidden_usernames=["admin", "staff"]
    )

    form_data = {}
    result = step.run_filter(form_data=form_data)

    assert result == form_data


def test_whitespace_username():
    """Test behavior with whitespace-only username."""
    step = PreventForbiddenUsernameRegistration(
        'org.openedx.learning.student.registration.requested.v1',
        'edx_filters_pipelines.auth.pipelines.registration.PreventForbiddenUsernameRegistration',
        forbidden_usernames=["admin", "staff"]
    )

    form_data = {"username": "   "}
    result = step.run_filter(form_data=form_data)

    assert result == form_data


def test_exception_properties():
    """Test that the exception has correct properties."""
    step = PreventForbiddenUsernameRegistration(
        'org.openedx.learning.student.registration.requested.v1',
        'edx_filters_pipelines.auth.pipelines.registration.PreventForbiddenUsernameRegistration',
        forbidden_usernames=["admin"]
    )

    form_data = {"username": "admin123"}

    with pytest.raises(StudentRegistrationRequested.PreventRegistration) as exc_info:
        step.run_filter(form_data=form_data)

    exception = exc_info.value
    assert hasattr(exception, 'status_code')
    assert hasattr(exception, 'error_code')
    # Note: We can't test exact values without accessing exception attributes
    # which may vary based on the openedx-filters implementation


def test_invalid_forbidden_config():
    """Test behavior when forbidden_usernames is not a list."""
    step = PreventForbiddenUsernameRegistration(
        'org.openedx.learning.student.registration.requested.v1',
        'edx_filters_pipelines.auth.pipelines.registration.PreventForbiddenUsernameRegistration',
        forbidden_usernames="admin"  # Should be a list, not a string
    )

    form_data = {"username": "admin123"}
    result = step.run_filter(form_data=form_data)

    # Should allow registration since invalid config is ignored
    assert result == form_data


def test_non_string_forbidden_terms():
    """Test behavior when forbidden list contains non-string values."""
    step = PreventForbiddenUsernameRegistration(
        'org.openedx.learning.student.registration.requested.v1',
        'edx_filters_pipelines.auth.pipelines.registration.PreventForbiddenUsernameRegistration',
        forbidden_usernames=["admin", 123, None, "staff"]  # Mixed types
    )

    form_data = {"username": "admin123"}

    with pytest.raises(StudentRegistrationRequested.PreventRegistration):
        step.run_filter(form_data=form_data)

    # Test that non-string forbidden terms are ignored
    form_data = {"username": "123"}
    result = step.run_filter(form_data=form_data)
    assert result == form_data
