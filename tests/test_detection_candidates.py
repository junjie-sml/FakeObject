import pytest
from PIL import Image
from src.detection.candidates import detection_queries,select_candidates
from src.app import service
from src.ui.detection import candidate_choices,candidate_gallery,detection_summary


def record(box,score=.5,query='building'):
    return {'box':box,'score':score,'label':query,'query':query}


def test_building_queries_and_explicit_descriptors():
    assert detection_queries('建筑')==['building']
    assert detection_queries('建筑','broad','塔楼，建筑立面;castle')==[
        'building','building facade','tower','architectural structure','castle']
    assert detection_queries('red cup on the left','broad')==['red cup on the left']
    with pytest.raises(ValueError): detection_queries('building','invalid')
    with pytest.raises(ValueError): detection_queries('building',extra_queries=','.join(str(i) for i in range(13)))


def test_dedup_keeps_nested_objects_and_distinct_instances():
    records=[record([0,0,100,100],.8),record([1,1,99,99],.7,'building facade'),
             record([20,10,50,50],.6,'tower'),record([110,0,190,100],.4)]
    selected,stats=select_candidates(records,(200,100))
    assert len(selected)==3 and stats['duplicate_count']==1
    assert selected[0]['queries']==['building','building facade']
    assert selected[1]['box']==[20,10,50,50]
    assert selected[2]['box']==[110,0,190,100]
    all_boxes,stats=select_candidates(records,(200,100),deduplicate=False)
    assert len(all_boxes)==4 and stats['duplicate_count']==0


def test_rank_cap_and_invalid_boxes_are_reported():
    records=[record([-5,-5,30,30],.2),record([50,0,90,40],.9),
             record([0,0,0,0]),record([float('nan'),0,2,3])]
    selected,stats=select_candidates(records,(80,80),max_candidates=1)
    assert selected[0]['box']==[50,0,80,40]
    assert stats['raw_count']==4 and stats['valid_count']==2 and stats['truncated_count']==1
    with pytest.raises(ValueError): select_candidates([], (100,100),max_candidates=101)


def test_multiple_candidate_masks_previews_and_selection_stay_aligned(monkeypatch,tmp_path):
    monkeypatch.setattr(service,'new_run',lambda:tmp_path)
    masks=[]
    for i,box in enumerate([(4,4,20,20),(32,32,60,60)]):
        mask=Image.new('L',(64,64)); mask.paste(255,box)
        path=tmp_path/f'candidate_{i}.png'; mask.save(path); masks.append(str(path))
    def worker(self,name,payload):
        assert payload['target']=='building' and payload['search_mode']=='broad'
        assert payload['threshold']==.15 and payload['max_candidates']==50
        return {'boxes':[[4,4,20,20],[32,32,60,60]],'scores':[.9,.2],
                'labels':['building','tower'],'masks':masks,'warnings':[],
                'search':{'mode':'broad','queries':['building','tower'],'threshold':.15,
                          'raw_count':3,'duplicate_count':1}}
    monkeypatch.setattr(service.ModelManager,'run',worker)
    detection=service.detect(Image.new('RGB',(64,64)),'建筑',search_mode='broad')
    assert len(detection['candidate_previews'])==2
    assert len(candidate_choices(detection))==len(candidate_gallery(detection))==2
    assert '较低' in candidate_choices(detection)[1][0]
    assert '2 个候选' in detection_summary(detection)
    with pytest.raises(ValueError,match='MULTIPLE_DETECTIONS'): service.select_mask(detection)
    assert service.select_mask(detection,1).getbbox()==(32,32,60,60)
    assert detection['target']=='建筑'
