from typing import Literal, Protocol
from pydantic import BaseModel, Field, ConfigDict

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Controls(StrictModel):
    novelty: float = Field(.75, ge=0, le=1)
    realism: float = Field(.90, ge=0, le=1)
    preservation: float = Field(.95, ge=0, le=1)
    geometry_complexity: float = Field(.55, ge=0, le=1)
    functional_ambiguity: float = Field(.75, ge=0, le=1)
    material_complexity: float = Field(.35, ge=0, le=1)

class Geometry(StrictModel):
    approximate_shape: str = 'match target bounding volume'
    apparent_size: str = 'same as original'
    orientation: str = 'match original'
    bounding_box_ratio: float | None = None

class Scene(StrictModel):
    support_surface: str = 'retain existing support'
    nearby_objects: list[str] = Field(default_factory=list)
    foreground_occlusions: list[str] = Field(default_factory=list)
    background_context: str = 'preserve original photograph'

class Lighting(StrictModel):
    direction: str = 'match source'
    softness: str = 'match source'
    color_temperature: str = 'match source'

class Camera(StrictModel):
    viewpoint: str = 'match source'
    depth_of_field: str = 'match source'

class FictionalObject(StrictModel):
    short_identifier: str
    conceptual_description: str
    primary_geometry: str
    secondary_structure: list[str] = Field(min_length=1, max_length=3)
    materials: list[str] = Field(min_length=1, max_length=3)
    colors: list[str] = Field(min_length=1, max_length=3)
    surface_properties: list[str]
    functional_implication: str
    asymmetry: str
    complexity: float = Field(ge=0, le=1)

class Scores(StrictModel):
    novelty_score: float = Field(0, ge=0, le=1)
    plausibility_score: float = Field(0, ge=0, le=1)
    preservation_score: float = Field(0, ge=0, le=1)
    specificity_score: float = Field(0, ge=0, le=1)
    method: str = 'textual heuristic; not visual evidence'

class FakeObjectSpec(StrictModel):
    raw_user_prompt: str
    target_object: str = Field(min_length=1)
    target_role_in_scene: str | None = None
    target_geometry: Geometry = Field(default_factory=Geometry)
    scene: Scene = Field(default_factory=Scene)
    lighting: Lighting = Field(default_factory=Lighting)
    camera: Camera = Field(default_factory=Camera)
    fictional_object: FictionalObject
    novelty_constraints: list[str]
    physical_constraints: list[str]
    preservation_constraints: list[str]
    prohibited_changes: list[str]
    negative_prompt: str = ''
    grounding_prompt: str
    final_edit_prompt: str = ''
    scores: Scores = Field(default_factory=Scores)
    seed: int
    mode: Literal['autonomous', 'user_concept', 'minimal_polish', 'exploration'] = 'autonomous'
    controls: Controls = Field(default_factory=Controls)
    warnings: list[str] = Field(default_factory=list)

class EditSpec(StrictModel):
    object_spec: FakeObjectSpec
    prompt_length: Literal['compact','standard','detailed'] = 'standard'

class PromptDesignerBackend(Protocol):
    def generate(self, raw_prompt: str, target: str, scene: dict, seed: int, **kwargs) -> list[FakeObjectSpec]: ...
