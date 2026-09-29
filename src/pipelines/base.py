from abc import ABC, abstractmethod
from pydantic import BaseModel, Field

class GroundingResult(BaseModel):
    boxes:list[list[float]] = Field(default_factory=list)
    scores:list[float] = Field(default_factory=list)
    labels:list[str] = Field(default_factory=list)
    masks:list[str] = Field(default_factory=list)
    selected_instance:int|None=None

class EditResult(BaseModel):
    run_id:str
    pipeline:str
    status:str
    output_dir:str
    original_image:str
    target_object:str
    grounding_result:dict=Field(default_factory=dict)
    selected_region:dict=Field(default_factory=dict)
    raw_mask:str|None=None
    processed_mask:str|None=None
    mask_visualization:str|None=None
    bbox_visualization:str|None=None
    scene_analysis:dict=Field(default_factory=dict)
    raw_user_prompt:str=''
    fake_object_spec:dict=Field(default_factory=dict)
    polished_prompt:str=''
    backend_prompt:str=''
    target_caption:str=''
    negative_prompt:str=''
    raw_model_output:str|None=None
    strict_output:str|None=None
    evaluation:dict=Field(default_factory=dict)
    runtime:dict=Field(default_factory=dict)
    hardware_stats:dict=Field(default_factory=dict)
    warnings:list[str]=Field(default_factory=list)
    model_versions:dict=Field(default_factory=dict)
    seed:int=42

class BaseEditPipeline(ABC):
    @abstractmethod
    def initialize(self): ...
    @abstractmethod
    def analyze_target(self, image, instruction, target=None): ...
    @abstractmethod
    def generate_mask(self, image, target, **kwargs): ...
    @abstractmethod
    def compile_prompt(self, spec): ...
    @abstractmethod
    def edit(self, **kwargs): ...
    @abstractmethod
    def unload(self): ...
    @abstractmethod
    def health_check(self): ...
