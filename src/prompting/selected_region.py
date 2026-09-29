"""Bind generation to the exact detection selected by the user."""
import hashlib
import re
import numpy as np
from src.prompting.language import grounding_phrase,TARGET_NAMES


def describe_selected_region(detection,index,mask):
    index=int(index)
    values=np.asarray(mask.convert('L'))>127
    yy,xx=np.where(values)
    if not len(xx): raise ValueError('Selected mask is empty.')
    height,width=values.shape
    box=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
    selected_box=detection['boxes'][index]
    contained=[]
    area=max(1,(selected_box[2]-selected_box[0])*(selected_box[3]-selected_box[1]))
    for i,other in enumerate(detection['boxes']):
        if i==index: continue
        other_area=max(1,(other[2]-other[0])*(other[3]-other[1]))
        intersection=max(0,min(selected_box[2],other[2])-max(selected_box[0],other[0]))*max(0,min(selected_box[3],other[3])-max(selected_box[1],other[1]))
        if other_area<area*.75 and intersection/other_area>.85:
            contained.append({'index':i,'label':detection['labels'][i]})
    return {'index':index,'display_number':index+1,'label':detection['labels'][index],
            'box':list(selected_box),'mask_box':box,
            'normalized_mask_box':[round(box[0]/width,3),round(box[1]/height,3),round(box[2]/width,3),round(box[3]/height,3)],
            'mask_pixels':int(values.sum()),'image_size':[width,height],
            'mask_sha256':hashlib.sha256(mask.convert('L').tobytes()).hexdigest(),
            'same_label_count':sum(label==detection['labels'][index] for label in detection['labels']),
            'contained_candidates':contained}


def bind_qwen_prompt(prompt,raw_user_prompt,region):
    label=grounding_phrase(region['label'])
    box=region['normalized_mask_box']
    building=label in ['building','house','architectural structure','building facade','house facade']
    chinese=bool(re.search('[\u4e00-\u9fff]',raw_user_prompt))
    if chinese:
        name=next((zh for zh,en in TARGET_NAMES.items() if en==label),label)
        instructions=f'将整个{name}的全部可见部分都按上述要求修改，包括上部、下部与左右两侧。保留目标以外的场景。'
        if building:
            instructions+='建筑的主体立面、下方结构、两侧墙面与屋顶都要按要求修改，保持原有布局；不能只改上部塔楼。'
    else:
        instructions=f'Apply the requested change to the entire {label}, including its visible lower and side sections. Preserve the surrounding scene.'
        if building:
            instructions+=' Transform its facade and both side sections, not just its upper tower or roof, keeping the original layout.'
    # Spatial coordinates help distinguish multiple instances of the same class;
    # avoid unnecessary localization jargon when the semantic name is unique.
    if region.get('same_label_count',1)>1:
        instructions+=f' Target extent: x={box[0]:.3f}..{box[2]:.3f}, y={box[1]:.3f}..{box[3]:.3f} (normalized image coordinates).'
    return (prompt if raw_user_prompt in prompt else raw_user_prompt+'\n'+prompt)+'\n'+instructions
