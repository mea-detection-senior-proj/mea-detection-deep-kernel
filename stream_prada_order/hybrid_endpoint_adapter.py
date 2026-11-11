"""Endpoint-aware software accounting, never scientific evaluation readiness.

Consumes existing calibrated metadata/aligned records and delegates decisions
and first-alert semantics to hybrid_fusion.evaluate(). No fitting, calibration,
score generation or file I/O. EndpointReport is a separate immutable Python
reporting record, not a replacement for historical Result or a wire schema.
"""
from dataclasses import dataclass

from . import hybrid_fusion as h
from . import hybrid_integration as a


PROFILE = 'research_256_grid_proposal_v1'


@dataclass(frozen=True)
class EndpointReport:
    """One method's by-Q250 accounting with explicit coverage/opportunity.

    complete refers to the selected method's required decisions; joint_complete
    refers to both components at every look. Only post_onset_status 'detected'
    or 'censored' describes a complete, at-risk post-onset observation. Neither
    status nor any_alert_by_q250 is a scientific performance estimate.
    """
    profile_id: str
    recorded_horizon: int
    evaluation_end: int
    spec: h.Spec
    stream: h.Stream
    method: str
    calibration_provenance: str
    threshold: h.Threshold
    points: tuple[h.Point, ...]
    decisions: tuple[bool | None, ...]
    checkpoints: tuple[int, ...]
    complete: bool
    joint_complete: bool
    any_alert_by_q250: bool | None
    first_observed_alert: int | None
    first_alert_query: int | None
    first_alert_exact: bool
    attack_onset: int | None
    pre_attack_alarm: bool | None
    scheduled_post_onset_opportunity: bool | None
    post_onset_status: str
    detection_delay: int | None
    censor_query: int | None


def evaluate_by_q250(model, rows, method, *, profile, attack_onset=None):
    """Report the exact 256/100/50/102 schedule with endpoint250.

    any_alert_by_q250 is True if any scheduled alert is observed, False only
    when all required decisions are observed and False, otherwise None. An
    observed event can coexist with unknown exact first-alert timing.
    No scheduled look exists after onset251..256: delay/censor remain None.
    All incomplete-path first-alert/delay semantics stay as in the evaluator.
    """
    h.require(type(profile) is str and profile == PROFILE, 'explicit_research_256_endpoint_profile_required')
    h.require(isinstance(model, h.Calibrated) and isinstance(model.normalizer, h.Normalizer)
              and isinstance(rows, h.Aligned), 'calibrated_model_and_aligned_records_required')
    expected = a.schedule(profile)
    h.require(isinstance(model.normalizer.spec, h.Spec) and isinstance(rows.spec, h.Spec)
              and model.normalizer.spec.schedule == rows.spec.schedule == expected
              and expected.checkpoints == (150, 200, 250), 'exact_endpoint_schedule_required')
    # This owns decisions, provenance/spec/disjointness checks and all existing
    # first-observed/exact/pre-attack/incomplete-path semantics.
    result = h.evaluate(model, rows, method, attack_onset=attack_onset)
    a.digest(result.calibration_provenance)
    threshold = model.thresholds[method]
    h.require(isinstance(threshold, h.Threshold)
              and (threshold.value is None or h.finite(threshold.value))
              and type(threshold.rank) is int and type(threshold.streams) is int
              and h.finite(threshold.alpha), 'immutable_calibrated_threshold_record_required')
    h.require(all(isinstance(p, h.Point) and type(p.query_index) is int for p in rows.points),
              'immutable_aligned_point_records_required')
    event = True if any(d is True for d in result.decisions) else False if result.complete else None
    opportunity = None
    if result.stream.label == 'benign':
        status = 'not_applicable_benign'
    elif result.attack_onset is None:
        status = 'onset_unknown'
    else:
        opportunity = any(t >= result.attack_onset for t in result.checkpoints)
        if not opportunity:
            status = 'no_scheduled_post_onset_opportunity'
        elif not result.complete:
            status = 'incomplete'
        elif result.pre_attack_alarm:
            status = 'pre_attack_alarm'
        elif result.censor_query is not None:
            status = 'censored'
        else:
            status = 'detected'
    # Only the no-alert administrative endpoint changes. The original Result
    # remains untouched, including its historical horizon256 censoring value.
    censor = 250 if opportunity is True and result.censor_query is not None else None
    delay = result.detection_delay if opportunity is True else None
    return EndpointReport(profile_id=profile, recorded_horizon=expected.horizon, evaluation_end=250,
        spec=rows.spec, stream=result.stream, method=result.method,
        calibration_provenance=result.calibration_provenance, threshold=threshold, points=tuple(rows.points),
        decisions=result.decisions, checkpoints=result.checkpoints, complete=result.complete,
        joint_complete=all(p.sequential_valid and p.mmd_valid for p in rows.points), any_alert_by_q250=event,
        first_observed_alert=result.first_observed_alert, first_alert_query=result.first_alert_query,
        first_alert_exact=result.first_alert_exact, attack_onset=result.attack_onset,
        pre_attack_alarm=result.pre_attack_alarm, scheduled_post_onset_opportunity=opportunity,
        post_onset_status=status, detection_delay=delay, censor_query=censor)
