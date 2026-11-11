"""Produce the existing common-stream contract from explicitly supplied metadata.

No query text, embeddings, models, network, detector scores or timestamps are
read or generated here. Evidence references must identify externally reviewed
authorization, ordering and physical byte-verification records. These Python
admission records do not extend or replace any hybrid v1 wire schema. Checking
their binding cannot authenticate a human declaration or reverify vector bytes.
"""
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from . import hybrid_fusion as h
from . import hybrid_integration as a


@dataclass(frozen=True)
class PhysicalEmbeddingEvidence:
    """References supplied by an external, reviewed physical embedding audit.

    receipt_sha256 identifies the actual private verification record and
    verifier_revision its pinned verifier source digest, not generated values.
    row_count/layout describe the canonical matrix whose digest is already in
    the representation. The index may cover a subset of that matrix's rows.
    """
    receipt_sha256: str
    verifier_revision: str
    embedding_artifact_sha256: str
    embedding_index_sha256: str
    representation_sha256: str
    row_count: int
    layout: str


@dataclass(frozen=True)
class SourceEvidence:
    """Caller-supplied admission evidence, never inferred from dataset order.

    authorized_manifest_sha256 binds the complete manifest including requests.
    chronology_record_sha256 identifies an observed-order audit for native
    traffic or a reviewed ordering specification for fixed-query replay.
    Group certificates and physical receipts must be authentic external inputs;
    this producer neither creates them nor certifies their truthfulness.
    """
    authorized: bool
    authorization_record_sha256: str
    authorized_manifest_sha256: str
    grouping_certificate_sha256: str
    chronology_kind: str
    chronology_basis: str
    chronology_record_sha256: str
    ordered_query_sha256: str
    physical_embeddings: PhysicalEmbeddingEvidence


def _verify_record(records, digest):
    """Require supplied record bytes, not merely a plausible digest string."""
    a.digest(digest)
    h.require(type(records) is dict and digest in records, 'evidence_record_required')
    raw = records[digest]
    h.require(type(raw) is bytes and 0 < len(raw) <= 1024**2, 'evidence_record_bytes_required')
    h.require(hashlib.sha256(raw).hexdigest() == digest, 'evidence_record_digest_mismatch')


def produce_manifest(metadata, ordered_requests, certificate, embedding_index, *,
                     expected_representation, evidence, evidence_records, profile):
    """Return a detached validated hybrid-common-stream-v1 manifest.

    metadata supplies every existing manifest field except queries; requests
    supplies that exact ordered list. Nothing is sorted, deduplicated, padded,
    renumbered or defaulted. expected_representation is the independently agreed
    detector representation, not a copy inferred by this function. The caller
    must supply an explicit existing integration profile (256 or 300).
    evidence_records maps SHA256 to actual immutable private record bytes for
    authorization, chronology, group audit and physical verification. Records
    are bounded to 1 MiB each and never emitted. Their authenticity/meaning
    still requires external review; digest checks are not signature checks.
    """
    h.require(type(metadata) is dict and 'queries' not in metadata, 'metadata_header_required')
    manifest = deepcopy(metadata)
    manifest['queries'] = deepcopy(ordered_requests)
    # All existing schema, sequence, identity, group and index checks stay here.
    a.validate_manifest(manifest, certificate, embedding_index, profile)
    a.embedding_contract(expected_representation)
    h.require(manifest['representation'] == expected_representation, 'expected_representation_mismatch')

    h.require(type(evidence) is SourceEvidence, 'source_evidence_required')
    h.require(evidence.authorized is True, 'explicit_authorized_source_required')
    for value in (evidence.authorization_record_sha256, evidence.authorized_manifest_sha256,
                  evidence.grouping_certificate_sha256, evidence.chronology_record_sha256,
                  evidence.ordered_query_sha256):
        a.digest(value)
    h.require(evidence.grouping_certificate_sha256 == h.fingerprint(certificate),
              'grouping_evidence_mismatch')
    h.require(evidence.chronology_kind == manifest['chronology_kind'], 'chronology_evidence_mismatch')
    basis = {'native': 'observed_request_order', 'fixed_query_replay': 'declared_fixed_replay'}
    h.require(evidence.chronology_basis == basis[manifest['chronology_kind']],
              'explicit_chronology_basis_required')
    h.require(evidence.ordered_query_sha256 == h.fingerprint(manifest['queries']),
              'ordered_query_evidence_mismatch')
    h.require(evidence.authorized_manifest_sha256 == h.fingerprint(manifest),
              'authorization_manifest_mismatch')

    physical = evidence.physical_embeddings
    h.require(type(physical) is PhysicalEmbeddingEvidence, 'physical_embedding_evidence_required')
    for value in (physical.receipt_sha256, physical.verifier_revision,
                  physical.embedding_artifact_sha256, physical.embedding_index_sha256,
                  physical.representation_sha256):
        a.digest(value)
    h.require(physical.embedding_artifact_sha256 == manifest['representation']['embedding_artifact_sha256']
              and physical.embedding_index_sha256 == h.fingerprint(embedding_index)
              and physical.representation_sha256 == h.fingerprint(expected_representation),
              'physical_embedding_evidence_mismatch')
    h.require(type(physical.row_count) is int and physical.row_count > 0
              and all(row['embedding_row'] < physical.row_count for row in embedding_index['rows'])
              and physical.layout == 'contiguous-little-endian', 'physical_embedding_layout_invalid')
    for digest in (evidence.authorization_record_sha256, evidence.chronology_record_sha256,
                   certificate['provenance_sha256'], physical.receipt_sha256):
        _verify_record(evidence_records, digest)
    return manifest


def write_manifest(output_path, **inputs):
    """Validate everything before opening a new file; never create directories.

    Returns the existing canonical manifest fingerprint. The file is exactly
    those canonical UTF-8 JSON bytes (no newline/envelope), so its SHA256 equals
    hybrid_fusion.fingerprint(manifest). Parent directory must already exist.
    Evidence references remain separate private admission records, not extra
    fields in the consumer manifest. Existing destinations are never replaced.
    """
    manifest = produce_manifest(**inputs)
    raw = json.dumps(manifest, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    fingerprint = h.fingerprint(manifest)
    with Path(output_path).open('xb') as stream:
        stream.write(raw)
    return fingerprint
