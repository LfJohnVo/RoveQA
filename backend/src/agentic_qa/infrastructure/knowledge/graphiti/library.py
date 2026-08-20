"""The one place graphiti-core is imported.

graphiti-core 0.29 still defines a pydantic model with the v1 class-based `Config`,
which raises a `DeprecationWarning` while its own module is being imported. The suite
runs with warnings as errors — deliberately, because a warning here has repeatedly
been a real defect — so that import has to be suppressed somewhere.

Suppressed *here*, around the import itself, rather than by adding an ignore to the
pytest configuration. A global ignore would also silence the same deprecation coming
from our own code, and this is a third-party problem that should stop being suppressed
the moment the library fixes it. Narrowing it to one import keeps that true.

Everything else imports graphiti through this module, so the suppression cannot be
bypassed by accident and there is exactly one comment explaining why it exists.
"""

import os
import warnings

# Set before the library loads: its telemetry is opt-out, and a local-first
# deployment does not report how much memory it is building to a third party.
os.environ.setdefault("GRAPHITI_TELEMETRY_ENABLED", "false")

with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore",
        message="Support for class-based `config` is deprecated",
        category=DeprecationWarning,
    )
    from graphiti_core.driver.driver import GraphProvider
    from graphiti_core.driver.falkordb_driver import FalkorDriver
    from graphiti_core.embedder.client import EmbedderClient
    from graphiti_core.graph_queries import get_fulltext_indices
    from graphiti_core.nodes import EntityNode

__all__ = [
    "EmbedderClient",
    "EntityNode",
    "FalkorDriver",
    "GraphProvider",
    "get_fulltext_indices",
]
