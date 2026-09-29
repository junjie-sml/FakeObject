from src.pipelines.base import BaseEditPipeline
from src.system.model_manager import ModelManager
from src.prompting.prompt_compiler import compile_prompt

class ModularPipeline(BaseEditPipeline):
    backend='qwen_image'
    def __init__(self): self.manager=ModelManager()
    def initialize(self): return self.health_check()
    def analyze_target(self,image,instruction,target=None):
        from src.app.service import infer_target
        return infer_target(instruction,target)
    def generate_mask(self,image,target,**kwargs):
        from src.app.service import detect
        return detect(image,target,**kwargs)
    def compile_prompt(self,spec): return compile_prompt(spec,self.backend)
    def edit(self,**kwargs):
        from src.app.service import run_edit
        return run_edit(pipeline=self.backend,**kwargs)
    def unload(self): self.manager.unload()
    def health_check(self): return self.manager.run(self.backend,{'action':'health'},timeout=120)
