"""Offline fusion of provenance-bound scores, never detector/model execution.

All indices are 1-based inclusive. Larger exported scores mean more anomalous.
Only synthetic numeric fixtures have been evaluated with this prototype.
"""
from bisect import bisect_right
from dataclasses import asdict, dataclass, field
from decimal import Decimal, ROUND_CEILING
import hashlib
import json
import math
from types import MappingProxyType
from typing import Mapping

METHODS=('sequential_only','mmd_only','or','and','weighted')


def require(ok,code):
    if not ok:raise ValueError(code)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def finite(value):return type(value) in (int,float) and math.isfinite(value)


@dataclass(frozen=True)
class Context:
    dataset_revision: str
    embedding_revision: str
    query_view_revision: str
    victim_revision: str

    def __post_init__(self):
        require(all(type(v) is str and v.strip() for v in asdict(self).values()),'context_provenance_required')


@dataclass(frozen=True)
class DetectorRevision:
    detector_revision: str
    model_revision: str
    configuration_revision: str
    calibration_provenance: str

    def __post_init__(self):
        require(all(type(v) is str and v.strip() for v in asdict(self).values()),'detector_provenance_required')


@dataclass(frozen=True)
class Schedule:
    horizon: int=300
    window: int=100
    stride: int=50
    first_eligible: int=102

    def __post_init__(self):
        require(all(type(x) is int and x>0 for x in asdict(self).values()),'schedule_positive_integers_required')

    @property
    def checkpoints(self):
        return tuple(t for t in range(self.window,self.horizon+1,self.stride) if t>=self.first_eligible)


@dataclass(frozen=True)
class Spec:
    context: Context
    sequential_revision: DetectorRevision
    mmd_revision: DetectorRevision
    schedule: Schedule=field(default_factory=Schedule)
    sequential_weight: float=.5

    def __post_init__(self):
        require(isinstance(self.context,Context) and isinstance(self.schedule,Schedule),'spec_types_invalid')
        require(isinstance(self.sequential_revision,DetectorRevision) and isinstance(self.mmd_revision,DetectorRevision),'spec_revisions_invalid')
        require(finite(self.sequential_weight) and 0<self.sequential_weight<1,'weight_invalid')


@dataclass(frozen=True)
class Stream:
    session_id: str
    ordered_query_sha256: str
    outer_group: str
    split: str
    label: str
    context: Context

    def __post_init__(self):
        require(type(self.session_id) is str and bool(self.session_id.strip()),'session_required')
        require(type(self.outer_group) is str and bool(self.outer_group.strip()),'outer_group_required')
        require(type(self.ordered_query_sha256) is str and len(self.ordered_query_sha256)==64
                and all(c in '0123456789abcdef' for c in self.ordered_query_sha256),'ordered_stream_digest_required')
        require(self.split in {'fit','calibration','validation','final_test','development'},'split_invalid')
        require(self.label in {'benign','attack'} and isinstance(self.context,Context),'label_or_context_invalid')


@dataclass(frozen=True)
class Score:
    stream: Stream
    revision: DetectorRevision
    start: int
    end: int
    available_at: int
    value: float | None
    valid: bool
    computed_through: int | None=None
    schema_version: str='hybrid-score-v1'
    orientation: str='higher_is_more_anomalous'

    def __post_init__(self):
        require(isinstance(self.stream,Stream) and isinstance(self.revision,DetectorRevision),'score_binding_invalid')
        require(self.schema_version=='hybrid-score-v1','score_version_invalid')
        require(self.orientation=='higher_is_more_anomalous','score_orientation_invalid')
        require(all(type(x) is int for x in (self.start,self.end,self.available_at))
                and 1<=self.start<=self.end<=self.available_at,'score_index_invalid')
        if self.computed_through is None:object.__setattr__(self,'computed_through',self.end)
        require(type(self.computed_through) is int and self.computed_through==self.end,'noncausal_score_dependency')
        require(type(self.valid) is bool,'validity_boolean_required')
        require(finite(self.value) if self.valid else self.value is None,'score_validity_value_mismatch')


@dataclass(frozen=True)
class Point:
    query_index: int
    sequential: float | None
    mmd: float | None
    sequential_reason: str
    mmd_reason: str

    @property
    def sequential_valid(self):return self.sequential_reason=='valid'
    @property
    def mmd_valid(self):return self.mmd_reason=='valid'


@dataclass(frozen=True)
class Aligned:
    spec: Spec
    stream: Stream
    points: tuple[Point,...]


def align(spec,stream,sequential,mmd):
    """Exact checkpoint values only; never carry old scores or backdate late ones."""
    require(stream.context==spec.context,'shared_context_mismatch')
    tables=[]
    for records,revision,is_mmd in [(sequential,spec.sequential_revision,False),(mmd,spec.mmd_revision,True)]:
        table={}
        for record in records:
            require(isinstance(record,Score) and record.stream==stream,'session_or_ordered_stream_mismatch')
            require(record.revision==revision,'detector_model_configuration_or_calibration_mismatch')
            require(record.end<=spec.schedule.horizon,'score_beyond_horizon')
            require(record.end not in table,'duplicate_score_endpoint')
            if is_mmd:
                require(record.start==record.end-spec.schedule.window+1 and
                        record.end>=spec.schedule.window and
                        (record.end-spec.schedule.window)%spec.schedule.stride==0,'mmd_window_grid_invalid')
            else:
                require(record.start==record.end,'sequential_query_index_invalid')
                require(record.end>=spec.schedule.first_eligible or not record.valid,'sequential_warmup_invalid')
            table[record.end]=record
        tables.append(table)
    def take(table,t):
        item=table.get(t)
        if item is None:
            return None,'stale' if any(q<t and r.available_at<=t for q,r in table.items()) else 'missing'
        if item.available_at>t:return None,'not_available'
        if not item.valid:return None,'invalid'
        return item.value,'valid'
    points=[]
    for t in spec.schedule.checkpoints:
        s,s_reason=take(tables[0],t);m,m_reason=take(tables[1],t)
        points.append(Point(t,s,m,s_reason,m_reason))
    return Aligned(spec,stream,tuple(points))


def checked(rows,spec):
    require(isinstance(rows,Aligned) and rows.spec==spec and rows.stream.context==spec.context,'alignment_spec_mismatch')
    require(tuple(p.query_index for p in rows.points)==spec.schedule.checkpoints and bool(rows.points),'checkpoint_coverage_invalid')
    for p in rows.points:
        for value,reason in [(p.sequential,p.sequential_reason),(p.mmd,p.mmd_reason)]:
            require(reason in {'valid','missing','stale','invalid','not_available'},'availability_reason_invalid')
            require(finite(value) if reason=='valid' else value is None,'aligned_validity_mismatch')


def units(rows,spec,split):
    rows=tuple(rows);require(bool(rows),'no_streams')
    keys=[]
    for r in rows:
        checked(r,spec)
        require(r.stream.split==split and r.stream.label=='benign','benign_split_required')
        require(all(p.sequential_valid and p.mmd_valid for p in r.points),'incomplete_fit_or_calibration_stream')
        keys.append((r.stream.session_id,r.stream.ordered_query_sha256,r.stream.outer_group))
    require(all(len({k[i] for k in keys})==len(keys) for i in range(3)),'duplicate_session_stream_or_outer_group')
    return rows,tuple(keys)


@dataclass(frozen=True)
class Normalizer:
    spec: Spec
    sequential_values: tuple[float,...]
    mmd_values: tuple[float,...]
    fit_units: tuple[tuple[str,str,str],...]
    provenance_sha256: str

    def transform(self,component,value):
        require(component in {'sequential','mmd'} and finite(value),'normalization_input_invalid')
        values=self.sequential_values if component=='sequential' else self.mmd_values
        return (1+bisect_right(values,value))/(len(values)+1)


def fit_normalizer(spec,streams):
    rows,keys=units(streams,spec,'fit')
    s=tuple(sorted(p.sequential for r in rows for p in r.points))
    m=tuple(sorted(p.mmd for r in rows for p in r.points))
    provenance=fingerprint({'schema':'hybrid-benign-fit-v1','spec':asdict(spec),'fit_units':keys,'sequential':s,'mmd':m})
    return Normalizer(spec,s,m,keys,provenance)


def fused(method,sequential,mmd,weight=.5):
    require(method in METHODS,'method_invalid')
    require(finite(weight) and 0<weight<1,'weight_invalid')
    require(all(x is None or finite(x) and 0<=x<=1 for x in (sequential,mmd)),'normalized_scores_required')
    if method=='sequential_only':return sequential
    if method=='mmd_only':return mmd
    if sequential is None or mmd is None:return None
    if method=='or':return max(sequential,mmd)
    if method=='and':return min(sequential,mmd)
    return weight*sequential+(1-weight)*mmd


def decision_fusion(operator,sequential,mmd):
    """Strict complete-pair OR/AND. Threshold provenance/calibration is external."""
    require(operator in {'or','and'},'operator_invalid')
    require(all(x is None or type(x) is bool for x in (sequential,mmd)),'boolean_decisions_required')
    if sequential is None or mmd is None:return None
    return sequential or mmd if operator=='or' else sequential and mmd


def values(normalizer,rows,method):
    checked(rows,normalizer.spec)
    result=[]
    for p in rows.points:
        s=normalizer.transform('sequential',p.sequential) if p.sequential_valid else None
        m=normalizer.transform('mmd',p.mmd) if p.mmd_valid else None
        result.append(fused(method,s,m,normalizer.spec.sequential_weight))
    return tuple(result)


def disjoint(left,right):
    require(all(not {k[i] for k in left}&{k[i] for k in right} for i in range(3)),'fit_calibration_evaluation_overlap')


@dataclass(frozen=True)
class Threshold:
    value: float | None  # None = +infinity/no-alert; JSON-safe, no tail extrapolation.
    rank: int
    streams: int
    alpha: float


@dataclass(frozen=True)
class Calibrated:
    normalizer: Normalizer
    calibration_units: tuple[tuple[str,str,str],...]
    thresholds: Mapping[str,Threshold]
    provenance_sha256: str

    def receipt(self):
        return {'schema_version':'hybrid-joint-calibration-v1','provenance_sha256':self.provenance_sha256,
                'normalizer_provenance_sha256':self.normalizer.provenance_sha256,
                'spec':asdict(self.normalizer.spec),'fit_units':self.normalizer.fit_units,
                'normalizer_values':{'sequential':self.normalizer.sequential_values,'mmd':self.normalizer.mmd_values},
                'calibration_units':self.calibration_units,
                'thresholds':{k:asdict(v) for k,v in self.thresholds.items()},
                'no_alert_threshold_encoding':None,'claim':'Rank bound requires exchangeable outer streams; declared groups do not prove independence.'}


def calibrate(normalizer,streams,alpha=.05):
    require(finite(alpha) and 0<alpha<1,'alpha_invalid')
    rows,keys=units(streams,normalizer.spec,'calibration');disjoint(normalizer.fit_units,keys)
    n=len(rows);rank=int((Decimal(n+1)*(1-Decimal(str(alpha)))).to_integral_value(rounding=ROUND_CEILING))
    thresholds={};maxima={}
    for method in METHODS:
        maxima[method]=sorted(max(values(normalizer,r,method)) for r in rows)
        thresholds[method]=Threshold(maxima[method][rank-1] if rank<=n else None,rank,n,alpha)
    provenance=fingerprint({'schema':'hybrid-joint-calibration-v1','normalizer':normalizer.provenance_sha256,
                            'units':keys,'alpha':alpha,'maxima':maxima,'rank':rank})
    return Calibrated(normalizer,keys,MappingProxyType(thresholds),provenance)


@dataclass(frozen=True)
class Result:
    stream: Stream
    method: str
    calibration_provenance: str
    decisions: tuple[bool | None,...]
    checkpoints: tuple[int,...]
    complete: bool
    first_observed_alert: int | None
    first_alert_query: int | None
    first_alert_exact: bool
    attack_onset: int | None
    pre_attack_alarm: bool | None
    detection_delay: int | None
    censor_query: int | None


def evaluate(model,rows,method,attack_onset=None):
    require(method in METHODS,'method_invalid')
    checked(rows,model.normalizer.spec)
    require(rows.stream.split in {'validation','final_test','development'},'evaluation_split_required')
    key=((rows.stream.session_id,rows.stream.ordered_query_sha256,rows.stream.outer_group),)
    disjoint((*model.normalizer.fit_units,*model.calibration_units),key)
    horizon=rows.spec.schedule.horizon
    require(attack_onset is None or type(attack_onset) is int and 1<=attack_onset<=horizon,'onset_invalid')
    require(attack_onset is None or rows.stream.label=='attack','benign_onset_conflict')
    threshold=model.thresholds[method].value
    scores=values(model.normalizer,rows,method)
    decisions=tuple(None if s is None else threshold is not None and s>threshold for s in scores)
    times=tuple(p.query_index for p in rows.points);complete=all(d is not None for d in decisions)
    index=next((i for i,d in enumerate(decisions) if d is True),None)
    observed=times[index] if index is not None else None
    exact=all(d is not None for d in decisions[:index+1]) if index is not None else complete
    first=observed if exact else None
    pre=delay=censor=None
    if complete and attack_onset is not None:
        if attack_onset>1:pre=first is not None and first<attack_onset
        if first is not None and first>=attack_onset:delay=first-attack_onset
        elif first is None:censor=horizon
    return Result(rows.stream,method,model.provenance_sha256,decisions,times,complete,observed,first,exact,
                  attack_onset,pre,delay,censor)


def false_alarm_counts(results):
    """One Bernoulli per declared outer group; repeated schedules cannot inflate n."""
    results=tuple(results)
    require(all(r.stream.label=='benign' and r.attack_onset is None for r in results),'benign_controls_required')
    require(len({r.stream.outer_group for r in results})==len(results),'repeated_outer_group_not_independent')
    require(len({r.stream.session_id for r in results})==len(results) and
            len({r.stream.ordered_query_sha256 for r in results})==len(results),'duplicate_evaluation_session_or_stream')
    require(len({r.method for r in results})<=1 and len({r.calibration_provenance for r in results})<=1,'mixed_methods_or_calibrations')
    complete=[r for r in results if r.complete];fp=sum(any(d is True for d in r.decisions) for r in complete)
    return {'total_streams':len(results),'complete_streams':len(complete),'incomplete':len(results)-len(complete),
            'false_alarm_streams':fp,'observed_alarm_streams_including_incomplete':sum(r.first_observed_alert is not None for r in results),
            'conditional_complete_stream_fpr':fp/len(complete) if complete else None,
            'scientific_status':'Accounting only; rates on numeric fixtures are not detection evidence.'}
