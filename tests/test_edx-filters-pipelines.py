"""
Tests for edx-filters-pipelines.py.
"""

import pytest
from edx_filters_pipelines.auth.pipelines.registration import PreventForbiddenUsernameRegistration
from openedx_filters.learning.filters import StudentRegistrationRequested

def test_username_blocked():
    step = PreventForbiddenUsernameRegistration(
        'org.openedx.learning.student.registration.requested.v1',
        'edx_filters_pipelines.auth.pipelines.registration.PreventForbiddenUsernameRegistration',
        forbidden_usernames= ["admin", "staff"]
    )
    
    form_data = {"username": "admin123"}
    
    with pytest.raises(StudentRegistrationRequested.PreventRegistration) as exc_info:
        step.run_filter(form_data=form_data)

    assert "admin" in str(exc_info.value)
