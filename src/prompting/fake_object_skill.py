from src.prompting.fake_object_designer import DeterministicDesigner
from src.prompting.schemas import Controls
from src.system.paths import config

def generate_concepts(prompt, target, scene=None, seed=42, preset='balanced', mode='autonomous', controls=None):
    values = config('fake_object_skill')['presets'][preset]
    return DeterministicDesigner().generate(prompt, target, scene, seed, mode, controls or Controls(**values))
