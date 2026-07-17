from pydantic import BaseModel,Field

class Args(BaseModel):
    content: str = Field(...,description="内容")