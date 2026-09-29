import numpy as np
import pytest
from PIL import Image
from src.postprocessing.mask_processor import process_mask
from src.postprocessing.compositor import strict_composite
from src.evaluation.metrics import evaluate

def test_cleanup_alpha_and_occlusion():
    m=np.zeros((100,100),dtype='uint8'); m[30:70,30:70]=255; m[5,5]=255; m[40,40]=0
    occ=np.zeros_like(m); occ[50:55,:]=255
    hard,alpha=process_mask(m,mask_dilation_px=4,preserve_occluders=occ)
    h=np.asarray(hard); a=np.asarray(alpha)
    assert h[5,5]==0 and h[40,40]==255 and h[28,40]==255
    assert not a[50:55].any() and not a[h==0].any()
    assert ((a>0)&(a<255)).any()

def test_strict_outside_exact_and_metrics_detect_drift():
    rng=np.random.default_rng(42)
    orig=Image.fromarray(rng.integers(0,256,(100,100,3),dtype='uint8')); gen=Image.new('RGB',(100,100),'white')
    mask=np.zeros((100,100),dtype='uint8'); mask[30:60,30:60]=255
    hard,alpha=process_mask(mask)
    result=strict_composite(orig,gen,alpha)
    outside=np.asarray(alpha)==0
    assert np.array_equal(np.asarray(orig)[outside],np.asarray(result)[outside])
    assert evaluate(orig,result,hard)['outside_exact']
    assert evaluate(orig,gen,hard)['outside_mae']>0

def test_empty_mask_errors_and_size_mismatch():
    with pytest.raises(ValueError,match='EMPTY_MASK'): process_mask(np.zeros((20,20)))
    with pytest.raises(ValueError): strict_composite(Image.new('RGB',(10,10)),Image.new('RGB',(9,9)),Image.new('L',(10,10)))

def test_object_interior_filling_is_optional_and_occluders_win():
    m=np.zeros((100,100),dtype='uint8'); m[10:90,10:90]=255; m[30:70,30:70]=0
    filled,_=process_mask(m,mask_dilation_px=0,fill_holes=True)
    unfilled,_=process_mask(m,mask_dilation_px=0,fill_holes=False)
    assert np.asarray(filled)[50,50]==255 and np.asarray(unfilled)[50,50]==0
    occ=np.zeros_like(m); occ[45:55,:]=255
    _,alpha=process_mask(m,preserve_occluders=occ)
    assert not np.asarray(alpha)[45:55].any()

def test_boolean_masks_and_scaled_dilation():
    mask=np.zeros((100,100),dtype=bool); mask[20:70,20:70]=True
    hard,_=process_mask(mask,mask_dilation_px=-1)
    assert np.asarray(hard)[19,40]==255
