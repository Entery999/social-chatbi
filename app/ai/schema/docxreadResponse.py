from pydantic import BaseModel, Field

class Args(BaseModel):
    path: str = Field(..., description="文件路径")