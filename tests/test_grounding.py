import pytest
from PIL import Image
from src.app.service import select_mask,infer_target,fingerprint

def test_multiple_detections_require_selection(tmp_path):
    p=tmp_path/'mask.png'; Image.new('L',(10,10),255).save(p)
    det={'masks':[str(p),str(p)]}
    with pytest.raises(ValueError,match='MULTIPLE_DETECTIONS'): select_mask(det)
    assert select_mask(det,1).getbbox() is not None
    with pytest.raises(ValueError): select_mask(det,2)

def test_intent_and_explicit_target():
    assert infer_target('Replace the red cup with something fictional.')=='red cup'
    assert infer_target('anything','mug')=='mug'
    assert infer_target('把杯子变成一种不存在的物体')=='杯子'
    with pytest.raises(ValueError): infer_target('make it weird')

def test_fingerprint_detects_content_and_size():
    assert fingerprint(Image.new('RGB',(10,10)))!=fingerprint(Image.new('RGB',(20,5)))
