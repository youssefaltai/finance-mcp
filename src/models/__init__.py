"""Pydantic models package."""

from pydantic import BaseModel, ConfigDict


class FinanceBaseModel(BaseModel):
    """Base model with shared config for all finance input models."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
