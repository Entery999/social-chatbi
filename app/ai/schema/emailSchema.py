from pydantic import BaseModel,Field

class EmailSchema(BaseModel):

    to:str = Field(...,description="收件人邮箱")
    subject:str = Field(...,description="主题")
    content:str =Field(...,description="内容")