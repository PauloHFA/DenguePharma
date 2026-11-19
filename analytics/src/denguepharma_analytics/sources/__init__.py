"""Adaptadores de fontes, resiliência de ingestão, snapshots e imutabilidade."""

from .ingestion_resilience import (
    BronzeRawSnapshot,
    BronzeRawSnapshotStore,
    ImmutableSnapshotError,
    IngestionCheckpointManager,
    IngestionRepository,
    LicenseEnforcer,
    LicenseRestrictionError,
    RateLimitError,
    ResilientFetcherWithBackoff,
    SearchRun,
    SourceDataManifest,
    SourceManifestEntry,
)

__all__ = [
    "ImmutableSnapshotError",
    "LicenseRestrictionError",
    "RateLimitError",
    "SearchRun",
    "IngestionRepository",
    "BronzeRawSnapshot",
    "BronzeRawSnapshotStore",
    "IngestionCheckpointManager",
    "ResilientFetcherWithBackoff",
    "LicenseEnforcer",
    "SourceManifestEntry",
    "SourceDataManifest",
]
