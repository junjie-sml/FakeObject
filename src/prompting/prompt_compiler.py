from src.prompting.model_adapters.brushedit_adapter import compile_brushedit
from src.prompting.model_adapters.qwen_adapter import compile_qwen
from src.prompting.schemas import EditSpec

def compile_prompt(spec, backend='qwen_image', length='standard'):
    canonical = EditSpec(object_spec=spec, prompt_length=length)
    return compile_brushedit(canonical.object_spec) if backend == 'brushedit' else compile_qwen(canonical.object_spec, length)
