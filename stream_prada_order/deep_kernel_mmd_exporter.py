"""Admission/export of precomputed active Deep Kernel MMD scores, never scoring.

No model/array libraries, checkpoint deserialization, embedding reads, file I/O
or numerical detector code. Private evidence records must be independently
reviewed; checking their bytes/bindings cannot certify opaque claims as true.
The output is the existing hybrid-producer-scores-v1 wire contract only.
"""
from dataclasses import asdict, dataclass
import hashlib

from . import common_stream_producer as common
from . import hybrid_fusion as h
from . import hybrid_integration as a


class MMDWindowsUnavailable(ValueError):
    """Missing authentic required windows, never a zero score or benign outcome."""


@dataclass(frozen=True)
class DeepKernelDefinition:
    """Reviewed method-global identity, shared across evaluation streams.

    source_revision is the active pipeline_source_sha256 from checkpoint
    provenance. protocol_lock_sha256 carries its original lock_id, not a new
    lock-file hash. Training/selection records must certify permitted memberships
    and pre-evaluation selection. Scoring configuration pins reviewed dependency,
    backend, precision and reference RNG policy. No per-stream score hashes enter
    this stamp.
    """
    source_revision: str
    protocol_lock_sha256: str
    input_dim: int
    hidden_dim: int
    feature_dim: int
    base_bandwidth: float
    feature_bandwidth: float
    epsilon: float
    dtype: str
    reference_repeats: int
    reference_manifest_sha256: str
    training_provenance_sha256: str
    selection_provenance_sha256: str
    scoring_configuration_sha256: str


@dataclass(frozen=True)
class CheckpointEvidence:
    checkpoint_identity: str
    checkpoint_sha256: str
    definition: DeepKernelDefinition
    format: str
    eval_mode: bool
    requires_grad: bool
    verification_record_sha256: str


@dataclass(frozen=True)
class ReferenceEvidence:
    reference_manifest_sha256: str
    embedding_artifact_sha256: str
    embedding_contract_sha256: str
    row_count: int
    layout: str
    frozen: bool
    physical_record_sha256: str
    provenance_record_sha256: str


@dataclass(frozen=True)
class MMDScoreEvidence:
    score_sha256: str
    manifest_sha256: str
    embedding_index_sha256: str
    revision: h.DetectorRevision
    definition: DeepKernelDefinition
    reference_manifest_sha256: str
    draws_sha256: str
    provenance_record_sha256: str
    draws_record_sha256: str


@dataclass(frozen=True)
class AvailabilityEvidence:
    score_sha256: str
    manifest_sha256: str
    basis: str
    window_availability: tuple[tuple[int, int, int], ...]
    record_sha256: str


def configuration_fingerprint(definition):
    """Stamp the reviewed active method; no training, selection or arithmetic."""
    h.require(type(definition) is DeepKernelDefinition, 'deep_kernel_definition_required')
    for digest in (definition.source_revision, definition.protocol_lock_sha256,
                   definition.reference_manifest_sha256, definition.training_provenance_sha256,
                   definition.selection_provenance_sha256, definition.scoring_configuration_sha256):
        a.digest(digest)
    h.require(all(type(n) is int and n > 0 for n in (definition.input_dim, definition.hidden_dim,
              definition.feature_dim, definition.reference_repeats)), 'deep_kernel_dimensions_or_repeats_invalid')
    h.require(h.finite(definition.base_bandwidth) and definition.base_bandwidth > 0
              and h.finite(definition.feature_bandwidth) and definition.feature_bandwidth > 0
              and h.finite(definition.epsilon) and 0 <= definition.epsilon <= 1
              and definition.dtype in {'float32', 'float64'}, 'deep_kernel_parameters_invalid')
    return h.fingerprint({**asdict(definition), 'embeddings': 'frozen',
        'feature_map': 'Linear-ReLU-Linear', 'kernel': '((1-epsilon)*feature_RBF+epsilon)*single_base_RBF',
        'bandwidths': 'trainable_exp', 'epsilon_parameterization': 'trainable_sigmoid',
        'training': 'pure_pairs_variance_normalized_J',
        'selection': 'maximum_fixed_validation_mean_J_including_epoch_zero',
        'estimator': 'all_cross_unbiased_MMD2', 'aggregation': 'mean_over_explicit_reference_draws',
        'reference_sampling': 'without_replacement_per_repeat', 'window': 100, 'stride': 50})


def _validate_checkpoint(checkpoint, definition, revision, records):
    h.require(type(checkpoint) is CheckpointEvidence, 'checkpoint_evidence_required')
    a.text(checkpoint.checkpoint_identity); a.digest(checkpoint.checkpoint_sha256)
    h.require(checkpoint.checkpoint_sha256 == revision.model_revision
              and checkpoint.definition == definition and checkpoint.format == 'mea-detection-deep-v1'
              and checkpoint.eval_mode is True and checkpoint.requires_grad is False,
              'frozen_active_checkpoint_identity_mismatch')
    for digest in (checkpoint.verification_record_sha256, definition.training_provenance_sha256,
                   definition.selection_provenance_sha256, definition.scoring_configuration_sha256):
        common._verify_record(records, digest)


def _validate_reference(reference, evidence, manifest, certificate, definition, records):
    a.validate_reference(reference, manifest, certificate)
    h.require(type(evidence) is ReferenceEvidence, 'physical_reference_evidence_required')
    for digest in (evidence.reference_manifest_sha256, evidence.embedding_artifact_sha256,
                   evidence.embedding_contract_sha256):
        a.digest(digest)
    h.require(evidence.reference_manifest_sha256 == definition.reference_manifest_sha256 == h.fingerprint(reference)
              and evidence.embedding_artifact_sha256 == reference['embedding_artifact_sha256']
              and evidence.embedding_contract_sha256 == a.embedding_contract(manifest['representation'])
              and type(evidence.row_count) is int and evidence.row_count == len(reference['rows'])
              and evidence.layout == 'contiguous-little-endian' and evidence.frozen is True,
              'frozen_reference_identity_or_layout_mismatch')
    for digest in (evidence.physical_record_sha256, evidence.provenance_record_sha256):
        common._verify_record(records, digest)


def export_deep_kernel_mmd(raw_scores, manifest, certificate, embedding_index, reference, *,
                           expected_representation, source_evidence, evidence_records, profile,
                           expected_revision, expected_definition, score_evidence, checkpoint_evidence,
                           reference_evidence, availability_evidence):
    """Export saved raw signed scores only, requiring the three joint windows.

    Raw UTF-8 JSON bytes contain a list of existing score-row records, including
    actual reference draws/validity/availability. [1,100] is optional; required
    windows end at150/200/250. Missing required rows raise MMDWindowsUnavailable,
    invalid rows remain null and late rows remain late. No partial payload,
    imputation, normalization, thresholding, sign change or new receipt is made.
    """
    h.require(profile == 'research_256_grid_proposal_v1', 'mmd_profile_not_supported')
    h.require(type(manifest) is dict and 'queries' in manifest, 'common_manifest_required')
    checked = common.produce_manifest({k: v for k, v in manifest.items() if k != 'queries'},
        manifest['queries'], certificate, embedding_index, expected_representation=expected_representation,
        evidence=source_evidence, evidence_records=evidence_records, profile=profile)
    h.require(type(score_evidence) is MMDScoreEvidence, 'mmd_score_provenance_unverified')
    h.require(type(availability_evidence) is AvailabilityEvidence, 'mmd_availability_evidence_required')
    h.require(isinstance(expected_revision, h.DetectorRevision), 'expected_mmd_revision_required')
    config = configuration_fingerprint(expected_definition)
    h.require(expected_definition.input_dim == checked['representation']['dimension'], 'feature_input_dimension_mismatch')
    h.require(score_evidence.definition == expected_definition and score_evidence.revision == expected_revision,
              'mmd_source_model_or_configuration_mismatch')
    h.require(expected_revision.detector_revision == expected_definition.source_revision
              and expected_revision.configuration_revision == config
              and expected_revision.calibration_provenance == expected_definition.selection_provenance_sha256,
              'mmd_revision_definition_mismatch')
    _validate_checkpoint(checkpoint_evidence, expected_definition, expected_revision, evidence_records)
    _validate_reference(reference, reference_evidence, checked, certificate, expected_definition, evidence_records)
    for digest in (score_evidence.score_sha256, score_evidence.manifest_sha256,
                   score_evidence.embedding_index_sha256, score_evidence.reference_manifest_sha256,
                   score_evidence.draws_sha256, availability_evidence.score_sha256, availability_evidence.manifest_sha256):
        a.digest(digest)
    h.require(score_evidence.manifest_sha256 == h.fingerprint(checked)
              and score_evidence.embedding_index_sha256 == h.fingerprint(embedding_index)
              and score_evidence.reference_manifest_sha256 == expected_definition.reference_manifest_sha256,
              'mmd_stream_embedding_or_reference_binding_mismatch')
    h.require(availability_evidence.score_sha256 == score_evidence.score_sha256
              and availability_evidence.manifest_sha256 == score_evidence.manifest_sha256,
              'availability_score_or_manifest_mismatch')
    for digest in (score_evidence.provenance_record_sha256, score_evidence.draws_record_sha256,
                   availability_evidence.record_sha256):
        common._verify_record(evidence_records, digest)
    if raw_scores is None or raw_scores == b'':
        raise MMDWindowsUnavailable('mmd_score_bytes_unavailable')
    h.require(type(raw_scores) is bytes and len(raw_scores) <= 8 * 1024**2, 'mmd_score_byte_cap')
    h.require(hashlib.sha256(raw_scores).hexdigest() == score_evidence.score_sha256, 'authentic_score_content_hash_mismatch')
    rows = a.strict_json(raw_scores)
    if type(rows) is not list or not rows or any(type(row) is not dict
            or not {'start', 'end', 'value'} <= set(row) for row in rows):
        raise MMDWindowsUnavailable('window_score_records_required_not_summary')
    h.require(all(type(row.get('computed_through')) is int for row in rows), 'explicit_causal_dependency_required')
    result = {'schema_version': 'hybrid-producer-scores-v1', 'kind': 'mmd_windows', 'profile_id': profile,
        'manifest_sha256': score_evidence.manifest_sha256,
        'representation_sha256': h.fingerprint(checked['representation']),
        'grouping_certificate_sha256': checked['grouping_certificate_sha256'], 'revision': asdict(expected_revision),
        'availability_basis': availability_evidence.basis,
        'reference_manifest_sha256': score_evidence.reference_manifest_sha256,
        'reference_repeats': expected_definition.reference_repeats, 'rows': rows}
    # Own no copies of row/window/draw validation logic: use the existing adapter.
    scores = a.export_scores(result, checked, certificate, embedding_index, expected_revision, profile, reference)
    if not {150, 200, 250} <= {score.end for score in scores}:
        raise MMDWindowsUnavailable('required_joint_MMD_windows_unavailable')
    draws = [{k: row[k] for k in ('start', 'end', 'reference_draws')} for row in rows]
    h.require(h.fingerprint(draws) == score_evidence.draws_sha256, 'authentic_reference_draw_binding_mismatch')
    availability = availability_evidence.window_availability
    h.require(type(availability) is tuple and all(type(item) is tuple and len(item) == 3
              and all(type(v) is int for v in item) for item in availability), 'explicit_window_availability_required')
    h.require(availability == tuple((s.start, s.end, s.available_at) for s in scores),
              'availability_evidence_does_not_match_saved_scores')
    return result
