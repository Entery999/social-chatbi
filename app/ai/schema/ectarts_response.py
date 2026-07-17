from pydantic import BaseModel,Field

class EchartsResponse(BaseModel):
    data: str = Field(...,description="json数据")
    code: int = Field(...,description="状态码")
    msg: str = Field(...,description="提示信息")