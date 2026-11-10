Change Log
##########

..
   All enhancements and patches to edx-filters-pipelines will be documented
   in this file.  It adheres to the structure of https://keepachangelog.com/ ,
   but in reStructuredText instead of Markdown (for ease of incorporation into
   Sphinx documentation and the PyPI description).

   This project adheres to Semantic Versioning (https://semver.org/).

.. There should always be an "Unreleased" section for changes pending release.

Unreleased
**********

1.2.1 - 2026-11-06
******************

Fixed
=====

* Management-command monitoring no longer breaks commands when there is no
  active Datadog root span (for example when ``manage.py`` is not run under
  ``ddtrace-run``). The command span is now opened first, and any monitoring
  setup error is logged instead of failing the command.

1.2.0 - 2026-11-04
******************

Added
=====

* Management-command monitoring pipeline support.

1.1.2 - 2026-08-07
******************

* Add Django 5.2 tox/CI coverage.
* Keep tox test deps on compiled requirement pins.

0.1.0 – 2025-08-05
**********************************************

Added
=====

* First release on PyPI.
