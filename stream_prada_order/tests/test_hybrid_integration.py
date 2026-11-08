"""Numeric-only metadata/score fixtures; never real chronology or embeddings."""
import copy
import dataclasses as dc
import json
from pathlib import Path
import unittest
from stream_prada_order import hybrid_fusion as h
from stream_prada_order import hybrid_integration as a

def sha(n):return h.fingerprint(n)
REV=h.DetectorRevision(sha(1),sha(2),sha(3),sha(4))
PROFILE='research_256_grid_proposal_v1'

def fixture(profile=PROFILE):
    n=a.schedule(profile).horizon
    cert={'schema_version':'hybrid-groups-v1','provenance_sha256':sha(1),'assignments':[
        {'source_group_sha256':sha(2),'outer_group':'1','split':'validation'},
        {'source_group_sha256':sha(3),'outer_group':'2','split':'fit'}]}
    rep={'encoder_id':'1','encoder_revision':sha(4),'tokenizer_revision':sha(5),'preprocessing_sha256':sha(6),
         'normalized':True,'dimension':2,'dtype':'float32','embedding_artifact_sha256':sha(7)}
    queries=[{'query_index':i+1,'request_id':str(i+1),'text_sha256':sha(i+1000),'embedding_row':i,
              'embedding_row_sha256':sha(i+2000),'source_group_sha256':sha(2)} for i in range(n)]
    manifest={'schema_version':'hybrid-common-stream-v1','session_id':'1','outer_group':'1','split':'validation','label':'benign',
        'chronology_kind':'fixed_query_replay','dataset_revision':sha(8),'victim_revision':sha(9),
        'grouping_certificate_sha256':sha(cert),'representation':rep,'queries':queries}
    index={'schema_version':'hybrid-embedding-index-v1','embedding_artifact_sha256':rep['embedding_artifact_sha256'],
        'representation_sha256':sha(rep),'rows':[{k:q[k] for k in ['embedding_row','text_sha256','embedding_row_sha256']} for q in queries]}
    refs={'schema_version':'hybrid-reference-v1','split':'fit','grouping_certificate_sha256':sha(cert),
        'embedding_contract_sha256':a.embedding_contract(rep),'embedding_artifact_sha256':sha(90),
        'rows':[{'text_sha256':sha(3000+i),'embedding_row_sha256':sha(4000+i),'source_group_sha256':sha(3),'outer_group':'2'} for i in range(100)]}
    return manifest,cert,index,refs

def payload(kind,manifest,refs=None,profile=PROFILE):
    sch=a.schedule(profile);ends=range(102,sch.horizon+1) if kind!='mmd_windows' else range(100,sch.horizon+1,50)
    rows=[]
    for end in ends:
        start=end if kind!='mmd_windows' else end-99
        rows.append({'start':start,'end':end,'available_at':end,'computed_through':end,'value':.9 if kind=='prada_w' else -.1 if kind=='mmd_windows' else 1.,
            'valid':True,'query_slice_sha256':sha(manifest['queries'][start-1:end]),
            'reference_draws':[list(range(100))] if kind=='mmd_windows' else None})
    return {'schema_version':'hybrid-producer-scores-v1','kind':kind,'profile_id':profile,
        'manifest_sha256':sha(manifest),'representation_sha256':sha(manifest['representation']),
        'grouping_certificate_sha256':manifest['grouping_certificate_sha256'],'revision':dc.asdict(REV),
        'availability_basis':'declared_fixed_replay','reference_manifest_sha256':sha(refs) if refs else None,
        'reference_repeats':1 if refs else 0,'rows':rows}

class ManifestTests(unittest.TestCase):
    def test_strict_json_rejects_duplicates_nonfinite_and_unknown_fields(self):
        for raw in [b'{"1":1,"1":2}',b'{"1":NaN}']:
            with self.assertRaises(ValueError):a.strict_json(raw)
        m,c,i,_=fixture();m['unknown']='1'
        with self.assertRaises(ValueError):a.validate_manifest(m,c,i,PROFILE)

    def test_profiles_are_explicit_preserve_both_schedules_and_config(self):
        self.assertEqual(a.schedule('illustrative_300_v1').checkpoints,(150,200,250,300))
        self.assertEqual(a.schedule(PROFILE).checkpoints,(150,200,250))
        with self.assertRaises(ValueError):a.schedule(None)
        cfg=json.loads((Path(__file__).resolve().parents[1]/'hybrid_integration_profiles_v1.json').read_bytes())
        for name,c in cfg['profiles'].items():self.assertEqual(list(a.schedule(name).checkpoints),c['joint_checkpoints'])

    def test_manifest_rows_representation_and_grouping_are_validated(self):
        m,c,i,_=fixture();stream=a.validate_manifest(m,c,i,PROFILE)
        self.assertEqual(stream.session_id,'1');self.assertEqual(stream.ordered_query_sha256,sha(m['queries']))
        for field,value in [('query_index',2),('embedding_row_sha256',sha(99)),('source_group_sha256',sha(88))]:
            bad=copy.deepcopy(m);bad['queries'][0][field]=value
            with self.assertRaises(ValueError):a.validate_manifest(bad,c,i,PROFILE)

    def test_wrong_artifact_group_split_and_horizon_rejected(self):
        m,c,i,_=fixture()
        for field,value in [('outer_group','9'),('split','fit')]:
            bad=copy.deepcopy(m);bad[field]=value
            with self.assertRaises(ValueError):a.validate_manifest(bad,c,i,PROFILE)
        bad=copy.deepcopy(i);bad['embedding_artifact_sha256']=sha(99)
        with self.assertRaises(ValueError):a.validate_manifest(m,c,bad,PROFILE)
        with self.assertRaises(ValueError):a.validate_manifest(m,c,i,'illustrative_300_v1')

    def test_repetitive_queries_allowed_but_request_ids_unique(self):
        m,c,i,_=fixture();m['queries'][1].update({k:m['queries'][0][k] for k in ['text_sha256','embedding_row','embedding_row_sha256']})
        a.validate_manifest(m,c,i,PROFILE)
        m['queries'][1]['request_id']=m['queries'][0]['request_id']
        with self.assertRaises(ValueError):a.validate_manifest(m,c,i,PROFILE)

    def test_group_certificate_cannot_assign_one_outer_group_to_two_splits(self):
        m,c,i,_=fixture();c['assignments'][1]['outer_group']='1';m['grouping_certificate_sha256']=sha(c)
        with self.assertRaises(ValueError):a.validate_manifest(m,c,i,PROFILE)

class AdapterTests(unittest.TestCase):
    def test_full_300_fixture_does_not_silently_truncate_to_256(self):
        profile='illustrative_300_v1';m,c,i,r=fixture(profile)
        aligned=a.align_exports(m,m,c,i,i,payload('prada_w',m,profile=profile),payload('mmd_windows',m,r,profile),REV,REV,r,profile)
        self.assertEqual([p.query_index for p in aligned.points],[150,200,250,300])
        with self.assertRaises(ValueError):a.validate_manifest(m,c,i,PROFILE)

    def test_same_stream_end_to_end_alignment_without_detector_calls(self):
        m,c,i,r=fixture();s=payload('prada_w',m);w=payload('mmd_windows',m,r)
        before=copy.deepcopy((m,c,i,r,s,w))
        aligned=a.align_exports(m,m,c,i,i,s,w,REV,REV,r,PROFILE)
        self.assertEqual([p.query_index for p in aligned.points],[150,200,250])
        self.assertTrue(all(p.sequential==-0.9 and p.mmd==-0.1 for p in aligned.points))
        self.assertEqual((m,c,i,r,s,w),before)

    def test_cusum_saved_curve_is_pass_through_not_recomputed(self):
        m,c,i,_=fixture();p=payload('cusum_curve',m)
        scores=a.export_scores(p,m,c,i,REV,PROFILE)
        self.assertEqual(scores[0].value,1.)
        bad={'max_score':1.,'first_alert':150}
        with self.assertRaises(ValueError):a.export_scores(bad,m,c,i,REV,PROFILE)

    def test_revision_manifest_and_embedding_mismatch_rejected(self):
        m,c,i,r=fixture();p=payload('mmd_windows',m,r)
        for field in ['manifest_sha256','representation_sha256','grouping_certificate_sha256']:
            bad=copy.deepcopy(p);bad[field]=sha(99)
            with self.assertRaises(ValueError):a.export_scores(bad,m,c,i,REV,PROFILE,r)
        with self.assertRaises(ValueError):a.export_scores(p,m,c,i,dc.replace(REV,model_revision=sha(99)),PROFILE,r)

    def test_windows_membership_and_terminal_256_not_invented(self):
        m,c,i,r=fixture();p=payload('mmd_windows',m,r)
        for change in [{'start':50},{'end':256,'start':157,'computed_through':256,'available_at':256},{'query_slice_sha256':sha(99)}]:
            bad=copy.deepcopy(p);bad['rows'][1].update(change)
            with self.assertRaises(ValueError):a.export_scores(bad,m,c,i,REV,PROFILE,r)

    def test_reference_draws_must_be_fit_disjoint_and_recorded(self):
        m,c,i,r=fixture();p=payload('mmd_windows',m,r)
        bad=copy.deepcopy(p);bad['rows'][0]['reference_draws']=[[0]*100]
        with self.assertRaises(ValueError):a.export_scores(bad,m,c,i,REV,PROFILE,r)
        badr=copy.deepcopy(r);badr['rows'][0]['outer_group']='1';bad=copy.deepcopy(p);bad['reference_manifest_sha256']=sha(badr)
        with self.assertRaises(ValueError):a.export_scores(bad,m,c,i,REV,PROFILE,badr)
        badr=copy.deepcopy(r);badr['rows'][0]['text_sha256']=m['queries'][0]['text_sha256']
        bad=copy.deepcopy(p);bad['reference_manifest_sha256']=sha(badr)
        with self.assertRaises(ValueError):a.export_scores(bad,m,c,i,REV,PROFILE,badr)
        bad=copy.deepcopy(p);bad['reference_repeats']=2
        with self.assertRaises(ValueError):a.export_scores(bad,m,c,i,REV,PROFILE,r)

    def test_missing_availability_future_dependency_and_duplicates_rejected(self):
        m,c,i,_=fixture();p=payload('prada_w',m)
        for mutate in [lambda b:b['rows'][0].pop('available_at'),lambda b:b['rows'][0].update(computed_through=256),
                       lambda b:b['rows'].append(copy.deepcopy(b['rows'][0]))]:
            bad=copy.deepcopy(p);mutate(bad)
            with self.assertRaises(ValueError):a.export_scores(bad,m,c,i,REV,PROFILE)

    def test_delayed_or_invalid_mmd_is_not_backfilled(self):
        m,c,i,r=fixture();s=payload('prada_w',m);w=payload('mmd_windows',m,r)
        w['rows'][1]['available_at']=151
        aligned=a.align_exports(m,m,c,i,i,s,w,REV,REV,r,PROFILE)
        self.assertEqual(aligned.points[0].mmd_reason,'not_available')
        w['rows'][1].update(valid=False,value=None)
        w['rows'][1]['available_at']=150
        self.assertEqual(a.align_exports(m,m,c,i,i,s,w,REV,REV,r,PROFILE).points[0].mmd_reason,'invalid')

    def test_unrelated_manifests_and_native_chronology_claim_rejected(self):
        m,c,i,r=fixture();other=copy.deepcopy(m);other['session_id']='2'
        with self.assertRaises(ValueError):a.align_exports(m,other,c,i,i,payload('prada_w',m),payload('mmd_windows',m,r),REV,REV,r,PROFILE)
        m['chronology_kind']='native';p=payload('prada_w',m)
        with self.assertRaises(ValueError):a.export_scores(p,m,c,i,REV,PROFILE)

    def test_authenticated_legacy_w_trace_requires_exact_order_and_availability(self):
        m,c,i,_=fixture();p=payload('prada_w',m)
        raw=json.dumps({'order':[q['embedding_row'] for q in m['queries']],
                        'w_steps':[r['end'] for r in p['rows']],'w':[r['value'] for r in p['rows']]}).encode()
        binding={k:v for k,v in p.items() if k!='rows'}
        binding.update(trace_sha256=__import__('hashlib').sha256(raw).hexdigest(),
                       available_at=[r['available_at'] for r in p['rows']])
        result=a.export_prada_trace(raw,binding,m,c,i,REV,PROFILE)
        self.assertEqual(result[0].value,-.9)
        bad=json.dumps({'order':[0]*256,'w_steps':[102],'w':[.9]}).encode()
        with self.assertRaises(ValueError):a.export_prada_trace(bad,binding,m,c,i,REV,PROFILE)
        binding.pop('available_at')
        with self.assertRaises(ValueError):a.export_prada_trace(raw,binding,m,c,i,REV,PROFILE)

    def test_old_mmd_csv_shape_is_not_accepted_as_score_manifest(self):
        m,c,i,r=fixture()
        with self.assertRaises(ValueError):a.export_scores({'window_id':0,'score':.1},m,c,i,REV,PROFILE,r)

if __name__=='__main__':unittest.main()
