"""Templates Tools Package.

After the 2026-07 cleanup, this package exposes only ``get_record_values``
(a generic record field read via the platform's ``GetPropertyValues`` API).

All other per-entity tools have been removed:

* Attribute CRUD (text, boolean, datetime, ...) — moved out of scope.
* Application / template / ontology tools — moved out of scope.
* Button / dataset / form / toolbar / record-template tools — moved out of scope.
* Record document / image attach and fetch — moved out of scope.
* Form builders and helpers — moved out of scope.

The HTTP transport that backs ``get_record_values`` is now inlined in
``tool_get_record_values.py`` (uses ``tools.requests_._post_request``); the
previous helper module ``tools.platform_record_document`` is gone.
"""

from tools.templates_tools.tool_get_record_values import get_record_values

__all__ = ["get_record_values"]
