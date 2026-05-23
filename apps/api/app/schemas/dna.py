from pydantic import BaseModel, Field
from typing import Optional


class PageMetadata(BaseModel):
    width_emu: int
    height_emu: int
    margin_top_emu: int
    margin_bottom_emu: int
    margin_left_emu: int
    margin_right_emu: int
    usable_width_emu: int

    @property
    def usable_width_pt(self) -> float:
        return self.usable_width_emu / 12700

    @property
    def usable_width_px(self) -> float:
        return self.usable_width_pt * 96 / 72


class TypographyMetadata(BaseModel):
    font_family: str = "Calibri"
    font_size: float = 10.0
    bold: bool = False
    italic: bool = False
    color: Optional[str] = None
    all_caps: bool = False
    alignment: str = "left"


class SpacingMetadata(BaseModel):
    space_before_pt: float = 0.0
    space_after_pt: float = 0.0
    line_spacing: Optional[float] = None
    line_spacing_rule: Optional[str] = None


class ConstraintMetadata(BaseModel):
    max_lines_per_bullet: int = 2
    max_chars_per_line: int = 95
    usable_width_pt: float = 0.0
    indent_left_pt: float = 0.0
    estimated_chars_per_line: int = 0


class BulletSchema(BaseModel):
    style_name: str
    typography: TypographyMetadata
    spacing: SpacingMetadata
    indent_left_emu: int = 0
    constraints: ConstraintMetadata


class SectionSchema(BaseModel):
    name: str
    section_type: str = "generic"
    order_index: int
    style_name: str
    typography: TypographyMetadata
    spacing: SpacingMetadata
    bullet_schema: Optional[BulletSchema] = None


class DocumentDNA(BaseModel):
    page: PageMetadata
    default_font_family: str = "Calibri"
    default_font_size: float = 10.0
    sections: list[SectionSchema] = Field(default_factory=list)
    bullet_schema: BulletSchema
    template_family: str = "mba_placement"
    raw_section_names: list[str] = Field(default_factory=list)
