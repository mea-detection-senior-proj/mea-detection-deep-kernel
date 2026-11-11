"""Admission-only export of saved CUSUM rows; no distance/CUSUM/model execution.

Input rows use the existing hybrid-producer-scores-v1 row fields. Evidence
dataclasses are separate admission inputs, not a new wire score schema. Caller
must retain raw curve bytes and reviewed sidecars with the exported payload.
Byte identity and declared bindings do not prove the truth of opaque receipts.
"""
from dataclasses import asdict, dataclass
import hashlib

from . import common_stream_producer as common
from . import hybrid_fusion as h
from . import hybrid_integration as a


class CurveUnavailable(ValueError):
    """No complete authenticated curve can be exported; never means score zero."""


@dataclass(frozen=True)
class CusumDefinition:
    """Frozen method-global definition shared across streams.

    upstream_provenance_sha256 identifies the reviewed PRADA/embedding-policy
    provenance. Stream-specific distance-history evidence belongs in the
    CurveEvidence provenance record, not in a per-stream detector revision.
    """
    direction: str
    k: float
    fit_parameters_sha256: str
    fit_provenance_sha256: str
    upstream_provenance_sha256: str


@dataclass(frozen=True)
class CurveEvidence:
    curve_sha256: str
    manifest_sha256: str
    embedding_index_sha256: str
    revision: h.DetectorRevision
    definition: CusumDefinition
    provenance_record_sha256: str


@dataclass(frozen=True)
class AvailabilityEvidence:
    curve_sha256: str
    manifest_sha256: str
    basis: str
    query_availability: tuple[tuple[int, int], ...]
    record_sha256: str


def configuration_fingerprint(definition):
    """Fingerprint declared Phase D semantics, never select a direction or k.

    model_revision is the raw saved distance_fit.json SHA256; configuration
    includes that identity, while calibration_provenance identifies benign fit
    provenance (not a new Hybrid calibration). No per-stream curve hashes enter
    detector revision stamps, so one frozen Spec can serve independent streams.
    """
    h.require(type(definition) is CusumDefinition, 'cusum_definition_required')
    h.require(definition.direction in {'upper', 'lower', 'two_sided'}, 'cusum_direction_invalid')
    h.require(h.finite(definition.k) and definition.k in (.5, 1.), 'cusum_k_not_documented_alternative')
    for digest in (definition.fit_parameters_sha256, definition.fit_provenance_sha256,
                   definition.upstream_provenance_sha256):
        a.digest(digest)
    return h.fingerprint({**asdict(definition), 'first_eligible_query': 102,
        'initial_state_before_first_eligible': 0., 'reset_policy': 'none', 'sigma_floor': .01,
        'distance_source': 'continuous_PRADA_Growing_Set_minimum_L2',
        'fit': 'benign_position_mean_and_sample_SD_Q2_through_Q256',
        'two_sided': 'current_max_of_upper_and_lower'})


def _validate_fit(definition, records):
    """Validate the saved Phase D fit artifact; never refit or standardize data."""
    for digest in (definition.fit_parameters_sha256, definition.fit_provenance_sha256,
                   definition.upstream_provenance_sha256):
        common._verify_record(records, digest)
    fit = a.strict_json(records[definition.fit_parameters_sha256])
    a.exact(fit, ['fit_cohorts', 'sigma_floor', 'mu', 'sigma'])
    cohorts = fit['fit_cohorts']
    h.require(type(cohorts) is list and len(cohorts) >= 2
              and all(type(i) is int and i >= 0 for i in cohorts)
              and len(set(cohorts)) == len(cohorts), 'benign_position_fit_cohorts_required')
    h.require(h.finite(fit['sigma_floor']) and fit['sigma_floor'] == .01, 'phase_d_sigma_floor_mismatch')
    h.require(type(fit['mu']) is list and type(fit['sigma']) is list
              and len(fit['mu']) == len(fit['sigma']) == 255
              and all(h.finite(v) for v in fit['mu'])
              and all(h.finite(v) and v >= .01 for v in fit['sigma']), 'position_fit_parameters_invalid')


def export_cusum_curve(raw_curve, manifest, certificate, embedding_index, *,
                       expected_representation, source_evidence, evidence_records, profile,
                       expected_revision, expected_definition, curve_evidence, availability_evidence):
    """Return only a validated existing hybrid-producer-scores-v1 payload.

    Supports the explicit proposed 256 profile; frozen 300-profile consumers
    remain unchanged. raw_curve is the exact already-computed JSON list of
    existing score-row records, including validity and availability, not a
    summary, distances, a new curve schema or an instruction to compute scores.
    Complete positions with invalid/late values remain invalid/late. Missing
    positions raise CurveUnavailable; no output or placeholder rows are made.
    """
    h.require(profile == 'research_256_grid_proposal_v1', 'cusum_profile_not_supported')
    # Reuse Task 02 admission, including authorization, chronology and physical
    # embedding evidence. No unreviewed manifest enters through a second path.
    h.require(type(manifest) is dict and 'queries' in manifest, 'common_manifest_required')
    checked_manifest = common.produce_manifest(
        {k: v for k, v in manifest.items() if k != 'queries'}, manifest['queries'], certificate, embedding_index,
        expected_representation=expected_representation, evidence=source_evidence,
        evidence_records=evidence_records, profile=profile)
    h.require(type(curve_evidence) is CurveEvidence, 'curve_provenance_unverified')
    h.require(type(availability_evidence) is AvailabilityEvidence, 'availability_evidence_required')
    h.require(isinstance(expected_revision, h.DetectorRevision), 'expected_detector_revision_required')
    config = configuration_fingerprint(expected_definition)
    h.require(curve_evidence.definition == expected_definition, 'cusum_direction_k_or_fit_mismatch')
    h.require(curve_evidence.revision == expected_revision, 'source_model_or_fit_revision_mismatch')
    h.require(expected_revision.configuration_revision == config
              and expected_revision.model_revision == expected_definition.fit_parameters_sha256
              and expected_revision.calibration_provenance == expected_definition.fit_provenance_sha256,
              'cusum_revision_definition_mismatch')
    for digest in (curve_evidence.curve_sha256, curve_evidence.manifest_sha256,
                   curve_evidence.embedding_index_sha256, curve_evidence.provenance_record_sha256,
                   availability_evidence.curve_sha256, availability_evidence.manifest_sha256,
                   availability_evidence.record_sha256):
        a.digest(digest)
    h.require(curve_evidence.manifest_sha256 == h.fingerprint(checked_manifest)
              and curve_evidence.embedding_index_sha256 == h.fingerprint(embedding_index),
              'curve_stream_or_embedding_binding_mismatch')
    h.require(availability_evidence.curve_sha256 == curve_evidence.curve_sha256
              and availability_evidence.manifest_sha256 == curve_evidence.manifest_sha256,
              'availability_curve_or_manifest_mismatch')
    for digest in (curve_evidence.provenance_record_sha256, availability_evidence.record_sha256):
        common._verify_record(evidence_records, digest)
    _validate_fit(expected_definition, evidence_records)

    if raw_curve is None or raw_curve == b'':
        raise CurveUnavailable('cusum_curve_bytes_unavailable')
    h.require(type(raw_curve) is bytes and len(raw_curve) <= 8 * 1024**2, 'cusum_curve_byte_cap')
    h.require(hashlib.sha256(raw_curve).hexdigest() == curve_evidence.curve_sha256,
              'authentic_curve_content_hash_mismatch')
    rows = a.strict_json(raw_curve)
    if type(rows) is not list or not rows or any(
            type(row) is not dict or not {'start', 'end', 'value'} <= set(row) for row in rows):
        raise CurveUnavailable('per_query_curve_required_not_summary')
    expected_positions = tuple(range(102, 257))
    if tuple(row['end'] for row in rows) != expected_positions:
        raise CurveUnavailable('complete_ordered_Q102_Q256_curve_unavailable')
    # Score allows a legacy None dependency default. This exporter requires the
    # authentic source to state computed_through explicitly, with no defaults.
    h.require(all(type(row.get('computed_through')) is int for row in rows),
              'explicit_causal_dependency_required')
    availability = availability_evidence.query_availability
    h.require(type(availability) is tuple and all(type(pair) is tuple and len(pair) == 2
              and all(type(v) is int for v in pair) for pair in availability),
              'explicit_query_availability_required')
    # The existing validator owns all row schema/value/index/causality checks.
    result = {'schema_version': 'hybrid-producer-scores-v1', 'kind': 'cusum_curve',
        'profile_id': profile, 'manifest_sha256': curve_evidence.manifest_sha256,
        'representation_sha256': h.fingerprint(checked_manifest['representation']),
        'grouping_certificate_sha256': checked_manifest['grouping_certificate_sha256'],
        'revision': asdict(expected_revision), 'availability_basis': availability_evidence.basis,
        'reference_manifest_sha256': None, 'reference_repeats': 0, 'rows': rows}
    scores = a.export_scores(result, checked_manifest, certificate, embedding_index, expected_revision, profile)
    h.require(availability == tuple((score.end, score.available_at) for score in scores),
              'availability_evidence_does_not_match_saved_curve')
    return result
