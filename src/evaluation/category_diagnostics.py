"""Optional real CLIP similarities; closed-set scores are explicitly not calibrated."""
import numpy as np
from PIL import Image
from src.system.paths import ROOT

def classify_crop(req):
    import torch
    from transformers import CLIPModel, CLIPProcessor
    local=ROOT/'models/clip'
    if not (local/'pytorch_model.bin').exists():
        return {'status':'NOT_MEASURED','reason':'Optional CLIP weights missing; download --model clip.'}
    image=Image.open(req['output']).convert('RGB'); mask=np.asarray(Image.open(req['mask']).convert('L'))>0
    yy,xx=np.where(mask)
    if not len(xx): raise ValueError('Empty evaluation mask')
    box=(int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1))
    crop=image.crop(box); original=Image.open(req['image']).convert('RGB').crop(box)
    categories=list(dict.fromkeys([req['target'],'cup','mug','bottle','vase','lamp','speaker','phone','camera','keyboard','mouse','watch','clock','chair','stool','table','container','box','toy','tool','appliance','helmet','shoe','bag','unfamiliar manufactured object']))
    processor=CLIPProcessor.from_pretrained(local,local_files_only=True)
    model=CLIPModel.from_pretrained(local,local_files_only=True).eval()
    inputs=processor(text=['a photo of a '+x for x in categories],images=[crop,original],return_tensors='pt',padding=True)
    with torch.inference_mode():
        out=model(**inputs); logits=out.logits_per_image; probs=logits.softmax(dim=-1)
        cosine=(out.image_embeds @ out.text_embeds.T).cpu().numpy()
    values=probs[0].cpu().numpy(); order=values.argsort()[::-1][:5]
    top=[{'category':categories[i],'cosine_similarity':float(cosine[0,i]),'closed_set_probability':float(values[i])} for i in order]
    source_index=categories.index(req['target'])
    return {'status':'MEASURED','model':'openai/clip-vit-base-patch32','top_category':top[0]['category'],'top_k':top,
            'entropy_nats':float(-(values*np.log(values+1e-12)).sum()),'category_count':len(categories),
            'source_similarity_original':float(cosine[1,source_index]),'source_similarity_generated':float(cosine[0,source_index]),
            'category_collapse_risk':'REVIEW' if top[0]['category']!='unfamiliar manufactured object' else 'INCONCLUSIVE',
            'note':'Single-model closed-set ranking, not calibrated confidence, not proof of novelty, realism, or source removal.'}
