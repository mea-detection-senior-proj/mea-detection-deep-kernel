"""Read-only score adapters. No detector imports, computation or inferred chronology.

Validates declared manifests/digests, not the physical embedding vectors or human
authorization. Production exporters must supply authentic provenance sidecars.
"""
from dataclasses import asdict
import hashlib
import json
from . import hybrid_fusion as h

ADAPTER_VERSION='hybrid-readonly-adapter-v1'


def exact(value,keys):
    h.require(type(value) is dict and set(value)==set(keys),'schema_keys_invalid')


def digest(value):
    h.require(type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value),'sha256_required')


def text(value):h.require(type(value) is str and bool(value.strip()),'nonempty_identifier_required')


def strict_json(raw):
    def pairs(items):
        result={}
        for k,v in items:
            h.require(k not in result,'duplicate_json_key');result[k]=v
        return result
    try:
        return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:h.require(False,'nonfinite_json'))
    except (json.JSONDecodeError,UnicodeError):raise ValueError('invalid_json') from None


def schedule(profile):
    h.require(profile in {'illustrative_300_v1','research_256_grid_proposal_v1'},'explicit_profile_required')
    return h.Schedule(horizon=300 if profile=='illustrative_300_v1' else 256)


def embedding_contract(representation):
    exact(representation,['encoder_id','encoder_revision','tokenizer_revision','preprocessing_sha256','normalized',
                          'dimension','dtype','embedding_artifact_sha256'])
    for key in ['encoder_id','encoder_revision','tokenizer_revision']:text(representation[key])
    for key in ['preprocessing_sha256','embedding_artifact_sha256']:digest(representation[key])
    h.require(type(representation['normalized']) is bool and type(representation['dimension']) is int
              and representation['dimension']>0 and representation['dtype'] in {'float32','float64'},'embedding_contract_invalid')
    return h.fingerprint({k:v for k,v in representation.items() if k!='embedding_artifact_sha256'})


def groups(certificate):
    exact(certificate,['schema_version','provenance_sha256','assignments'])
    h.require(certificate['schema_version']=='hybrid-groups-v1','group_schema_invalid');digest(certificate['provenance_sha256'])
    h.require(type(certificate['assignments']) is list and bool(certificate['assignments']),'group_assignments_missing')
    by_source={};by_outer={}
    for row in certificate['assignments']:
        exact(row,['source_group_sha256','outer_group','split']);digest(row['source_group_sha256']);text(row['outer_group'])
        h.require(row['split'] in {'fit','calibration','validation','development','final_test'},'group_split_invalid')
        h.require(row['source_group_sha256'] not in by_source,'duplicate_source_group')
        h.require(by_outer.get(row['outer_group'],row['split'])==row['split'],'outer_group_cross_split')
        by_outer[row['outer_group']]=row['split'];by_source[row['source_group_sha256']]=row
    return by_source


def validate_manifest(manifest,certificate,index,profile):
    sch=schedule(profile)
    exact(manifest,['schema_version','session_id','outer_group','split','label','chronology_kind','dataset_revision',
                    'victim_revision','grouping_certificate_sha256','representation','queries'])
    h.require(manifest['schema_version']=='hybrid-common-stream-v1','manifest_schema_invalid')
    h.require(manifest['chronology_kind'] in {'native','fixed_query_replay'},'chronology_kind_required')
    for k in ['session_id','outer_group','dataset_revision','victim_revision']:text(manifest[k])
    h.require(manifest['grouping_certificate_sha256']==h.fingerprint(certificate),'group_certificate_mismatch')
    assignments=groups(certificate);rep=manifest['representation'];contract=embedding_contract(rep)
    exact(index,['schema_version','embedding_artifact_sha256','representation_sha256','rows'])
    h.require(index['schema_version']=='hybrid-embedding-index-v1'
              and index['embedding_artifact_sha256']==rep['embedding_artifact_sha256']
              and index['representation_sha256']==h.fingerprint(rep),'embedding_index_binding_mismatch')
    h.require(type(index['rows']) is list,'embedding_index_rows_required');vectors={}
    for row in index['rows']:
        exact(row,['embedding_row','text_sha256','embedding_row_sha256'])
        h.require(type(row['embedding_row']) is int and row['embedding_row']>=0 and row['embedding_row'] not in vectors,'embedding_row_duplicate_or_invalid')
        digest(row['text_sha256']);digest(row['embedding_row_sha256']);vectors[row['embedding_row']]=row
    queries=manifest['queries'];h.require(type(queries) is list and len(queries)==sch.horizon,'exact_horizon_required_no_padding_or_truncation')
    ids=set()
    for position,q in enumerate(queries,1):
        exact(q,['query_index','request_id','text_sha256','embedding_row','embedding_row_sha256','source_group_sha256'])
        h.require(type(q['query_index']) is int and q['query_index']==position,'query_positions_not_contiguous')
        text(q['request_id']);h.require(q['request_id'] not in ids,'duplicate_request_id');ids.add(q['request_id'])
        for k in ['text_sha256','embedding_row_sha256','source_group_sha256']:digest(q[k])
        h.require(type(q['embedding_row']) is int and q['embedding_row']>=0,'embedding_row_invalid')
        expected={k:q[k] for k in ['embedding_row','text_sha256','embedding_row_sha256']}
        h.require(vectors.get(q['embedding_row'])==expected,'query_embedding_row_mismatch')
        assignment=assignments.get(q['source_group_sha256'])
        h.require(assignment is not None and assignment['outer_group']==manifest['outer_group']
                  and assignment['split']==manifest['split'],'source_group_membership_or_split_mismatch')
    context=h.Context(manifest['dataset_revision'],contract,rep['preprocessing_sha256'],manifest['victim_revision'])
    return h.Stream(manifest['session_id'],h.fingerprint(queries),manifest['outer_group'],manifest['split'],manifest['label'],context)


def validate_reference(reference,manifest,certificate):
    exact(reference,['schema_version','split','grouping_certificate_sha256','embedding_contract_sha256','embedding_artifact_sha256','rows'])
    h.require(reference['schema_version']=='hybrid-reference-v1' and reference['split']=='fit','fit_reference_required')
    h.require(reference['grouping_certificate_sha256']==h.fingerprint(certificate)
              and reference['embedding_contract_sha256']==embedding_contract(manifest['representation']),'reference_binding_mismatch')
    digest(reference['embedding_artifact_sha256']);assignments=groups(certificate)
    h.require(type(reference['rows']) is list and len(reference['rows'])>=100,'reference_bank_too_small')
    queries={q['text_sha256'] for q in manifest['queries']}
    for row in reference['rows']:
        exact(row,['text_sha256','embedding_row_sha256','source_group_sha256','outer_group'])
        for k in ['text_sha256','embedding_row_sha256','source_group_sha256']:digest(row[k])
        text(row['outer_group']);assignment=assignments.get(row['source_group_sha256'])
        h.require(assignment is not None and assignment['split']=='fit' and assignment['outer_group']==row['outer_group'],'reference_source_not_fit')
        h.require(row['outer_group']!=manifest['outer_group'] and row['text_sha256'] not in queries,'reference_query_or_group_leakage')


PAYLOAD_KEYS=['schema_version','kind','profile_id','manifest_sha256','representation_sha256','grouping_certificate_sha256',
              'revision','availability_basis','reference_manifest_sha256','reference_repeats','rows']


def adapted_revision(revision,kind,profile,reference_sha=None):
    return h.DetectorRevision(revision.detector_revision,revision.model_revision,
        h.fingerprint({'adapter':ADAPTER_VERSION,'producer_configuration':revision.configuration_revision,
                       'kind':kind,'profile':profile,'orientation':'negative_W' if kind=='prada_w' else 'identity'}),
        h.fingerprint({'producer_provenance':revision.calibration_provenance,'reference_manifest':reference_sha}))


def export_scores(payload,manifest,certificate,index,expected_revision,profile,reference=None):
    """Convert supplied scores only; return immutable records, never write source files."""
    stream=validate_manifest(manifest,certificate,index,profile);sch=schedule(profile);exact(payload,PAYLOAD_KEYS)
    h.require(payload['schema_version']=='hybrid-producer-scores-v1' and payload['kind'] in {'prada_w','cusum_curve','mmd_windows'},'producer_schema_or_kind_invalid')
    h.require(payload['profile_id']==profile and payload['manifest_sha256']==h.fingerprint(manifest)
              and payload['representation_sha256']==h.fingerprint(manifest['representation'])
              and payload['grouping_certificate_sha256']==manifest['grouping_certificate_sha256'],'producer_manifest_binding_mismatch')
    h.require(isinstance(expected_revision,h.DetectorRevision) and payload['revision']==asdict(expected_revision),'producer_revision_mismatch')
    basis=payload['availability_basis']
    h.require(basis in {'observed_query_position','declared_fixed_replay'},'availability_basis_required')
    h.require(basis!='declared_fixed_replay' or manifest['chronology_kind']=='fixed_query_replay','cannot_invent_native_chronology')
    mmd=payload['kind']=='mmd_windows';repeats=payload['reference_repeats']
    h.require(type(repeats) is int and (repeats>0 if mmd else repeats==0),'reference_repeat_count_invalid')
    if mmd:
        h.require(reference is not None and payload['reference_manifest_sha256']==h.fingerprint(reference),'actual_reference_manifest_required')
        validate_reference(reference,manifest,certificate)
    else:h.require(reference is None and payload['reference_manifest_sha256'] is None,'sequential_reference_not_applicable')
    revision=adapted_revision(expected_revision,payload['kind'],profile,payload['reference_manifest_sha256'])
    h.require(type(payload['rows']) is list,'score_rows_required');scores=[];seen=set()
    for row in payload['rows']:
        exact(row,['start','end','available_at','computed_through','value','valid','query_slice_sha256','reference_draws'])
        # Score validates strict types, finite values, direction, availability and causal dependencies.
        score=h.Score(stream,revision,row['start'],row['end'],row['available_at'],row['value'],row['valid'],row['computed_through'])
        h.require(score.end<=sch.horizon and score.end not in seen,'duplicate_or_out_of_horizon_score');seen.add(score.end)
        if mmd:
            h.require(score.start==score.end-sch.window+1 and score.end>=sch.window
                      and (score.end-sch.window)%sch.stride==0,'mmd_window_grid_invalid')
            draws=row['reference_draws']
            if draws is None:h.require(not score.valid,'valid_mmd_reference_draws_missing')
            else:
                h.require(type(draws) is list and len(draws)==repeats,'reference_repeats_mismatch')
                for draw in draws:
                    h.require(type(draw) is list and len(draw)==sch.window and
                              all(type(x) is int and 0<=x<len(reference['rows']) for x in draw)
                              and len(set(draw))==len(draw),'reference_draw_invalid_or_replacement_not_declared')
        else:
            h.require(score.start==score.end and score.end>=sch.first_eligible and row['reference_draws'] is None,'sequential_index_or_reference_invalid')
            if score.valid:
                h.require(0<=score.value<=1 if payload['kind']=='prada_w' else score.value>=0,'sequential_score_range_invalid')
        h.require(row['query_slice_sha256']==h.fingerprint(manifest['queries'][score.start-1:score.end]),'window_query_membership_mismatch')
        value=-score.value if payload['kind']=='prada_w' and score.valid else score.value
        scores.append(h.Score(stream,revision,score.start,score.end,score.available_at,value,score.valid,score.computed_through))
    return tuple(scores)


def export_prada_trace(raw,binding,manifest,certificate,index,expected_revision,profile):
    """Legacy saved W path only, gated by exact bytes/order and supplied availability.

    No Shapiro/CUSUM recomputation and no implicit available_at=query_index.
    Historical local order indices must refer to the supplied embedding table.
    """
    h.require(type(raw) is bytes and len(raw)<=8*1024**2,'trace_read_cap')
    exact(binding,[k for k in PAYLOAD_KEYS if k!='rows']+['trace_sha256','available_at'])
    h.require(binding['kind']=='prada_w' and binding['trace_sha256']==hashlib.sha256(raw).hexdigest(),'trace_identity_mismatch')
    validate_manifest(manifest,certificate,index,profile);trace=strict_json(raw)
    h.require(type(trace) is dict and {'order','w_steps','w'}<=set(trace),'legacy_w_path_missing')
    h.require(type(trace['order']) is list and all(type(x) is int for x in trace['order'])
              and trace['order']==[q['embedding_row'] for q in manifest['queries']],'legacy_order_not_common_embedding_rows')
    steps=list(range(schedule(profile).first_eligible,schedule(profile).horizon+1))
    h.require(type(trace['w_steps']) is list and all(type(x) is int for x in trace['w_steps']) and trace['w_steps']==steps
              and type(trace['w']) is list and len(trace['w'])==len(steps),'legacy_w_path_incomplete')
    h.require(type(binding['available_at']) is list and len(binding['available_at'])==len(steps),'actual_availability_required')
    payload={k:binding[k] for k in PAYLOAD_KEYS if k!='rows'}
    payload['rows']=[{'start':t,'end':t,'available_at':available,'computed_through':t,'value':w,'valid':True,
                      'query_slice_sha256':h.fingerprint(manifest['queries'][t-1:t]),'reference_draws':None}
                     for t,w,available in zip(steps,trace['w'],binding['available_at'])]
    return export_scores(payload,manifest,certificate,index,expected_revision,profile)


def align_exports(sequential_manifest,mmd_manifest,certificate,sequential_index,mmd_index,
                  sequential_payload,mmd_payload,sequential_revision,mmd_revision,reference,profile):
    left=validate_manifest(sequential_manifest,certificate,sequential_index,profile)
    right=validate_manifest(mmd_manifest,certificate,mmd_index,profile)
    h.require(sequential_manifest==mmd_manifest and sequential_index==mmd_index and left==right,'unrelated_stream_or_embedding_manifests')
    h.require(sequential_payload.get('kind') in {'prada_w','cusum_curve'} and mmd_payload.get('kind')=='mmd_windows','detector_roles_invalid')
    seq=export_scores(sequential_payload,sequential_manifest,certificate,sequential_index,sequential_revision,profile)
    mmd=export_scores(mmd_payload,mmd_manifest,certificate,mmd_index,mmd_revision,profile,reference)
    spec=h.Spec(left.context,adapted_revision(sequential_revision,sequential_payload['kind'],profile),
                adapted_revision(mmd_revision,'mmd_windows',profile,mmd_payload['reference_manifest_sha256']),schedule(profile))
    return h.align(spec,left,seq,mmd)
