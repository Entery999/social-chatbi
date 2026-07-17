from pydantic import BaseModel,Field
class EmailResponse(BaseModel):
    data:str = Field(...)
    subject:str = Field(...,description="验证码")
    code : str = Field(...,description="状态码")
    msg : str = Field(...,description="提示信息")




