from src.prompting.model_adapters.qwen_adapter import compile_qwen
from src.prompting.schemas import EditSpec

def compile_prompt(spec, backend='qwen_image', length='standard'):
    if backend != 'qwen_image': raise ValueError('Only qwen_image is supported.')
    canonical = EditSpec(object_spec=spec, prompt_length=length)
    return compile_qwen(canonical.object_spec, length)
