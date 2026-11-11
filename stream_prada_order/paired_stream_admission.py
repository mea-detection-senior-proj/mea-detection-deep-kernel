"""Software-only paired admission: no scoring, calibration or evaluation.

Trusted expectations are explicit separate arguments, never producer defaults.
Only existing exporters can supply payloads to align_exports(). Success means
contract admission, not authentic-artifact certification/scientific readiness.
No file I/O; no private record bytes or exception text enters diagnostics.
"""
from dataclasses import dataclass, fields, is_dataclass
import hashlib

from . import common_stream_producer as common
from . import cusum_curve_exporter as c
from . import deep_kernel_mmd_exporter as m
from . import hybrid_fusion as h
from . import hybrid_integration as a


@dataclass(frozen=True, kw_only=True)
class CUSUMInputs:
    manifest: dict
    certificate: dict
    embedding_index: dict
    source_evidence: common.SourceEvidence
    evidence_records: dict[str, bytes]
    raw_curve: bytes | None
    curve_evidence: c.CurveEvidence | None
    availability_evidence: c.AvailabilityEvidence | None


@dataclass(frozen=True, kw_only=True)
class DeepKernelInputs:
    manifest: dict
    certificate: dict
    embedding_index: dict
    source_evidence: common.SourceEvidence
    evidence_records: dict[str, bytes]
    raw_scores: bytes | None
    reference: dict
    score_evidence: m.MMDScoreEvidence | None
    checkpoint_evidence: m.CheckpointEvidence | None
    reference_evidence: m.ReferenceEvidence | None
    availability_evidence: m.AvailabilityEvidence | None


@dataclass(frozen=True)
class InputFingerprints:
    cusum_input_sha256: str
    mmd_input_sha256: str
    expectations_sha256: str
    common_manifest_sha256: str
    ordered_query_sha256: str
    embedding_index_sha256: str
    grouping_certificate_sha256: str
    reference_manifest_sha256: str
    cusum_curve_sha256: str
    mmd_score_sha256: str
    cusum_payload_sha256: str
    mmd_payload_sha256: str


@dataclass(frozen=True)
class JointAvailability:
    query_index: int
    cusum_available: bool
    mmd_available: bool
    joint_available: bool


@dataclass(frozen=True)
class PairedAlignment:
    profile_id: str
    identities: InputFingerprints
    cusum_revision: h.DetectorRevision
    mmd_revision: h.DetectorRevision
    aligned: h.Aligned
    cusum_scores: tuple[h.Score, ...]
    mmd_scores: tuple[h.Score, ...]
    joint_availability: tuple[JointAvailability, ...]
    joint_complete: bool


@dataclass(frozen=True)
class AdmissionDiagnostic:
    stage: str
    code: str


@dataclass(frozen=True)
class AdmissionResult:
    contract_admitted: bool
    pair: PairedAlignment | None
    diagnostic: AdmissionDiagnostic | None


class _Rejected(ValueError):
    """Only this module's fixed, public rule codes, never input values."""


def _require(condition, code):
    if not condition: raise _Rejected(code)


# Generic ValueError is not automatically a data rejection. Recognize explicit
# validation raise sites in the frozen dependencies; unknown errors propagate.
# This avoids copying their validators/error catalogs or exposing exception text.
_VALIDATION_ORIGINS = (h.require.__code__, a.strict_json.__code__)
_CUSUM_ORIGIN = c.export_cusum_curve.__code__
_MMD_ORIGIN = m.export_deep_kernel_mmd.__code__


def _rejection_code(error):
    trace = error.__traceback__
    while trace.tb_next is not None: trace = trace.tb_next
    origin = trace.tb_frame.f_code
    if type(error) is c.CurveUnavailable and origin is _CUSUM_ORIGIN:
        return 'cusum_curve_unavailable'
    if type(error) is m.MMDWindowsUnavailable and origin is _MMD_ORIGIN:
        return 'mmd_windows_unavailable'
    if type(error) is ValueError and origin in _VALIDATION_ORIGINS:
        return 'contract_rejected'
    return None


def _identity(value):
    """Canonical metadata projection; bytes become actual digest+length only.

    Dataclass name/fields are tagged, dict keys remain strings, tuple/list order
    is preserved as JSON arrays. Existing h.fingerprint supplies canonical JSON.
    This is an in-memory identity projection, never another score wire schema.
    """
    if type(value) is bytes:
        return {'raw_bytes_sha256': hashlib.sha256(value).hexdigest(), 'byte_count': len(value)}
    if is_dataclass(value) and not isinstance(value, type):
        return {'dataclass': type(value).__name__,
                'fields': {field.name: _identity(getattr(value, field.name)) for field in fields(value)}}
    if type(value) is dict:
        _require(all(type(key) is str for key in value), 'identity_keys_must_be_strings')
        return {key: _identity(item) for key, item in value.items()}
    if type(value) in (tuple, list): return [_identity(item) for item in value]
    _require(value is None or type(value) in (str, bool, int, float), 'unsupported_identity_metadata')
    return value


def _fingerprint(value): return h.fingerprint(_identity(value))


def admit_and_align(cusum, deep_kernel, *, profile, expected_representation,
                    expected_cusum_revision, expected_cusum_definition,
                    expected_mmd_revision, expected_mmd_definition):
    """Admit both producers or return no pair. Expected identities are mandatory.

    contract_admitted=True can coexist with joint_complete=False for valid
    contracts containing invalid/late rows. Rejections expose stage/code only;
    unexpected programming errors, including unknown ValueErrors, propagate.
    Inputs/sidecars remain with the caller; result containers are immutable and
    contain only fingerprints, library records, raw scores and coverage metadata.
    """
    stage = 'inputs'
    try:
        _require(type(profile) is str and profile == 'research_256_grid_proposal_v1', 'explicit_profile_required')
        _require(type(cusum) is CUSUMInputs and type(deep_kernel) is DeepKernelInputs, 'producer_inputs_required')
        stage = 'expectations'
        a.embedding_contract(expected_representation)
        _require(type(expected_cusum_revision) is h.DetectorRevision
                 and type(expected_mmd_revision) is h.DetectorRevision, 'independent_revisions_required')
        c.configuration_fingerprint(expected_cusum_definition)
        m.configuration_fingerprint(expected_mmd_definition)
        stage = 'shared_identity'
        _require(cusum.manifest == deep_kernel.manifest, 'common_manifest_mismatch')
        _require(cusum.embedding_index == deep_kernel.embedding_index, 'embedding_index_mismatch')
        _require(cusum.certificate == deep_kernel.certificate, 'group_certificate_mismatch')
        stage = 'cusum_export'
        sequential = c.export_cusum_curve(cusum.raw_curve, cusum.manifest, cusum.certificate, cusum.embedding_index,
            expected_representation=expected_representation, source_evidence=cusum.source_evidence,
            evidence_records=cusum.evidence_records, profile=profile,
            expected_revision=expected_cusum_revision, expected_definition=expected_cusum_definition,
            curve_evidence=cusum.curve_evidence, availability_evidence=cusum.availability_evidence)
        stage = 'mmd_export'
        windows = m.export_deep_kernel_mmd(deep_kernel.raw_scores, deep_kernel.manifest, deep_kernel.certificate,
            deep_kernel.embedding_index, deep_kernel.reference, expected_representation=expected_representation,
            source_evidence=deep_kernel.source_evidence, evidence_records=deep_kernel.evidence_records,
            profile=profile, expected_revision=expected_mmd_revision, expected_definition=expected_mmd_definition,
            score_evidence=deep_kernel.score_evidence, checkpoint_evidence=deep_kernel.checkpoint_evidence,
            reference_evidence=deep_kernel.reference_evidence, availability_evidence=deep_kernel.availability_evidence)
        stage = 'alignment'
        aligned = a.align_exports(cusum.manifest, deep_kernel.manifest, cusum.certificate,
            cusum.embedding_index, deep_kernel.embedding_index, sequential, windows,
            expected_cusum_revision, expected_mmd_revision, deep_kernel.reference, profile)
        # Reuse the adapter to retain immutable raw scores/actual availability;
        # align_exports itself returns only checkpoint points, not the full paths.
        sequential_scores = a.export_scores(sequential, cusum.manifest, cusum.certificate,
            cusum.embedding_index, expected_cusum_revision, profile)
        window_scores = a.export_scores(windows, deep_kernel.manifest, deep_kernel.certificate,
            deep_kernel.embedding_index, expected_mmd_revision, profile, deep_kernel.reference)
        stage = 'fingerprints'
        for records in (cusum.evidence_records, deep_kernel.evidence_records):
            _require(all(type(key) is str and type(raw) is bytes for key, raw in records.items()),
                     'evidence_records_require_string_keys_and_bytes')
        identities = InputFingerprints(_fingerprint(cusum), _fingerprint(deep_kernel),
            _fingerprint({'representation': expected_representation, 'cusum_revision': expected_cusum_revision,
                'cusum_definition': expected_cusum_definition, 'mmd_revision': expected_mmd_revision,
                'mmd_definition': expected_mmd_definition, 'profile': profile}),
            h.fingerprint(cusum.manifest), h.fingerprint(cusum.manifest['queries']),
            h.fingerprint(cusum.embedding_index), h.fingerprint(cusum.certificate),
            h.fingerprint(deep_kernel.reference), hashlib.sha256(cusum.raw_curve).hexdigest(),
            hashlib.sha256(deep_kernel.raw_scores).hexdigest(), h.fingerprint(sequential), h.fingerprint(windows))
        availability = tuple(JointAvailability(pt.query_index, pt.sequential_valid, pt.mmd_valid,
            pt.sequential_valid and pt.mmd_valid) for pt in aligned.points)
        pair = PairedAlignment(profile, identities, expected_cusum_revision, expected_mmd_revision,
            aligned, sequential_scores, window_scores, availability, all(look.joint_available for look in availability))
        return AdmissionResult(True, pair, None)
    except _Rejected as error:
        return AdmissionResult(False, None, AdmissionDiagnostic(stage, error.args[0]))
    except ValueError as error:
        code = _rejection_code(error)
        if code is None: raise
        return AdmissionResult(False, None, AdmissionDiagnostic(stage, code))
