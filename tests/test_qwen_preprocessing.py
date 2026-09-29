"""CPU regression against the installed Qwen processor; no model weights loaded.

Run with envs/qwen_image/Scripts/python.exe -m unittest discover -s tests
    -p test_qwen_preprocessing.py -v
The orchestrator suite skips this module when Qwen dependencies are absent.
"""
import unittest
from PIL import Image
from src.system.paths import ROOT
from src.workers.common import resize_for_inference
from src.workers.qwen_worker import configure_condition_processor

try:
    from transformers import AutoProcessor
    from diffusers.pipelines.qwenimage21.pipeline_qwenimage21 import calculate_dimensions
    HAS_QWEN=True
except ImportError:
    HAS_QWEN=False


@unittest.skipUnless(HAS_QWEN and (ROOT/'models/qwen_image/processor').exists(),
                     'Run in the Qwen environment with the local processor files.')
class QwenConditionGridTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.processor=AutoProcessor.from_pretrained(ROOT/'models/qwen_image/processor',local_files_only=True)

    def token_counts(self,size,max_side=512,reference_count=2):
        small=resize_for_inference(Image.new('RGB',size),max_side,32)
        w,h,_=calculate_dimensions(max(small.size)**2,small.width/small.height)
        reference=small.resize((w,h))
        inputs=self.processor(
            text=['<|vision_start|><|image_pad|><|vision_end|> '*reference_count+'Replace the building.'],
            images=[reference]*reference_count,return_tensors='pt')
        token_id=self.processor.tokenizer.convert_tokens_to_ids('<|image_pad|>')
        slots=int((inputs.input_ids==token_id).sum())
        target_tokens=small.width//16*(small.height//16)
        vae_tokens=reference_count*(w//16)*(h//16)+target_tokens
        transformer_slots=4*slots+target_tokens
        return vae_tokens,transformer_slots,inputs.image_grid_thw.tolist(),(w,h)

    def test_original_small_photo_reproduces_reported_mismatch(self):
        self.processor.image_processor.do_resize=True
        self.assertEqual(self.token_counts((270,196))[:2],(696,832))

    def test_shared_grid_for_small_portrait_landscape_square_and_preview(self):
        configure_condition_processor(self.processor)
        for size,max_side in [((270,196),512),((196,270),512),((200,200),512),
                              ((100,50),512),((1024,256),512),((640,480),512),
                              ((640,480),384),((1600,1200),768),((1600,1200),1024)]:
            with self.subTest(size=size,max_side=max_side):
                latents,slots,grids,(w,h)=self.token_counts(size,max_side)
                self.assertEqual(latents,slots)
                self.assertEqual(grids,[[1,h//16,w//16]]*2)

    def test_small_photo_uses_requested_generation_resolution(self):
        configure_condition_processor(self.processor)
        image=resize_for_inference(Image.new('RGB',(270,196)),512,32,allow_upscale=True)
        self.assertEqual(image.size,(512,352))
        for count in [1,2]:
            latents,slots,grids,(w,h)=self.token_counts(image.size,reference_count=count)
            self.assertEqual(latents,slots)
            self.assertEqual(grids,[[1,h//16,w//16]]*count)


if __name__=='__main__': unittest.main()
