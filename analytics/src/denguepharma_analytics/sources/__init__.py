"""Adaptadores de fontes, resiliência de ingestão, snapshots e imutabilidade."""

from .ingestion_resilience import (
    ImmutableSnapshotError,
    LicenseRestrictionError,
    RateLimitError,
    SearchRun,
    IngestionRepository,
    BronzeRawSnapshot,
    BronzeRawSnapshotStore,
    IngestionCheckpointManager,
    ResilientFetcherWithBackoff,
    LicenseEnforcer,
    SourceManifestEntry,
    SourceDataManifest,
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
