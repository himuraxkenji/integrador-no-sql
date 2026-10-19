from pydantic import BaseModel, Field


class Customer(BaseModel):
    id: str
    name: str
    email: str
    interests: list[str] = Field(default_factory=list)  # categorías de interés
