edx-filters-pipelines
#####################


|pyversions-badge|
|license-badge| |status-badge|

Purpose
*******

``edx-filters-pipelines`` is a private Python package for **edx.org** that extends
`openedx-filters <https://github.com/openedx/openedx-filters>`_ by adding custom
pipelines specific to edx.org.  

These pipelines enforce
edx.org–specific business rules and behaviors across platform events such as
registration, authentication, and course access.

Features
========

1. Provides edx.org–specific filter pipelines that plug into the Open edX system.
2. Implements custom validation and enforcement logic (e.g., username restrictions).
3. Fully compatible with the ``OPEN_EDX_FILTERS_CONFIG`` setting in ``edx-platform``.

Getting Started with Development
********************************

Please see the Open edX documentation for `guidance on Python development`_ in this repo.

.. _guidance on Python development: https://docs.openedx.org/en/latest/developers/how-tos/get-ready-for-python-dev.html

Deploying
*********

Since this is a private repo, installation is handled via GitHub with an access token:

.. code-block:: bash

   pip install git+https://<your-token>@github.com/edx/edx-filters-pipelines.git@<tag>#egg=edx-filters-pipelines

Make sure deployment agents have access to this private repo before installing.

(TODO: `How to add private requirements to edx-platform documentation <https://2u-internal.atlassian.net/wiki/spaces/AT/pages/396034066/How+to+add+private+requirements+to+edx-platform>`_)


Getting Help
************

Documentation
=============

Configuration
=============

To use the pipelines, configure them in your ``edx-platform`` settings via
``OPEN_EDX_FILTERS_CONFIG``:

.. code-block:: python

   OPEN_EDX_FILTERS_CONFIG = {
       "org.openedx.filter.type.v1": {
           "pipeline": [
               "path.to.pipeline.CustomPipeline"
           ],
           "fail_silently": False,
       }
   }

- **filter_type** → The event name defined by an ``OpenEdxPublicFilter`` (e.g., ``"org.openedx.learning.student.registration.requested.v1"``).  
- **pipeline** → Full Python import path to your ``PipelineStep`` class.  
- **fail_silently** → If ``True``, errors are ignored; if ``False``, exceptions are raised.  

Concepts
========

- **OpenEdxPublicFilter** → Declares a filter hook (event). Defines the event name, data context, and any exceptions.  
- **PipelineStep** → Implements the logic that runs when the filter is triggered.  
- **OPEN_EDX_FILTERS_CONFIG** → Wires filters to pipeline implementations.  

Example
=======

.. code-block:: python

Below are generic examples showing how to define and use **Filters** and **Pipeline Steps** with
``edx-filters-pipelines``.
Below are generic examples showing how to define and use **Filters** and **Pipeline Steps** with
``edx-filters-pipelines``.

.. code-block:: python
Filter Example
~~~~~~~~~~~~~~

.. code-block:: python

    from openedx_filters.tooling import OpenEdxPublicFilter

    class CustomFilter(OpenEdxPublicFilter):
        """
        Example filter used to modify the process in the LMS.

        Filter Type:
            org.openedx.filter.type.v1

        Trigger:
            - Repository: openedx/edx-platform
            - Path: path/to/function/
            - Method: View.post
        """

        filter_type = "org.openedx.filter.type.v1"


Pipeline Example
~~~~~~~~~~~~~~~~

.. code-block:: python

    from edx_filters_pipelines.pipelines.base import PipelineStep

    class CustomPipeline(PipelineStep):
        """
        Pipeline that adds functionality to filter type
        """
        def run_filter(self, data, **kwargs):
            return data

More Help
=========

If you're having trouble, we have discussion forums at
https://discuss.openedx.org where you can connect with others in the
community.

Our real-time conversations are on Slack. You can request a `Slack
invitation`_, then join our `community Slack workspace`_.

For anything non-trivial, the best path is to open an issue in this
repository with as many details about the issue you are facing as you
can provide.

https://github.com/edx/edx-filters-pipelines/issues

For more information about these options, see the `Getting Help <https://openedx.org/getting-help>`__ page.

.. _Slack invitation: https://openedx.org/slack
.. _community Slack workspace: https://openedx.slack.com/

License
*******

The code in this repository is licensed under the AGPL 3.0 unless
otherwise noted.

Please see `LICENSE.txt <LICENSE.txt>`_ for details.

Contributing
************

Contributions are very welcome.
Please read `How To Contribute <https://openedx.org/r/how-to-contribute>`_ for details.

This project is currently accepting all types of contributions, bug fixes,
security fixes, maintenance work, or new features.  However, please make sure
to discuss your new feature idea with the maintainers before beginning development
to maximize the chances of your change being accepted.
You can start a conversation by creating a new issue on this repo summarizing
your idea.

The Open edX Code of Conduct
****************************

All community members are expected to follow the `Open edX Code of Conduct`_.

.. _Open edX Code of Conduct: https://openedx.org/code-of-conduct/

People
******

The assigned maintainers for this component and other project details may be
found in `Backstage`_. Backstage pulls this data from the ``catalog-info.yaml``
file in this repo.

.. _Backstage: https://backstage.openedx.org/catalog/default/component/edx-filters-pipelines

Reporting Security Issues
*************************

Please do not report security issues in public. Please email security@openedx.org.

.. |pypi-badge| image:: https://img.shields.io/pypi/v/edx-filters-pipelines.svg
    :target: https://pypi.python.org/pypi/edx-filters-pipelines/
    :alt: PyPI

.. |ci-badge| image:: https://github.com/edx/edx-filters-pipelines/actions/workflows/ci.yml/badge.svg?branch=main
    :target: https://github.com/edx/edx-filters-pipelines/actions/workflows/ci.yml
    :alt: CI

.. |codecov-badge| image:: https://codecov.io/github/edx/edx-filters-pipelines/coverage.svg?branch=main
    :target: https://codecov.io/github/edx/edx-filters-pipelines?branch=main
    :alt: Codecov

.. |doc-badge| image:: https://readthedocs.org/projects/edx-filters-pipelines/badge/?version=latest
    :target: https://docs.openedx.org/projects/edx-filters-pipelines
    :alt: Documentation

.. |pyversions-badge| image:: https://img.shields.io/pypi/pyversions/edx-filters-pipelines.svg
    :target: https://pypi.python.org/pypi/edx-filters-pipelines/
    :alt: Supported Python versions

.. |license-badge| image:: https://img.shields.io/github/license/edx/edx-filters-pipelines.svg
    :target: https://github.com/edx/edx-filters-pipelines/blob/main/LICENSE.txt
    :alt: License

.. TODO: Choose one of the statuses below and remove the other status-badge lines.
.. |status-badge| image:: https://img.shields.io/badge/Status-Experimental-yellow
.. .. |status-badge| image:: https://img.shields.io/badge/Status-Maintained-brightgreen
.. .. |status-badge| image:: https://img.shields.io/badge/Status-Deprecated-orange
.. .. |status-badge| image:: https://img.shields.io/badge/Status-Unsupported-red
