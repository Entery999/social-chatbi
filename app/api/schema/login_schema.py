from pydantic import BaseModel, Field

# 登陆发送验证码
class SendCodeSchema(BaseModel):
    email: str = Field(..., example="邮箱")

# 登陆请求接口
class LoginSchema(BaseModel):
    email: str = Field(..., example="邮箱")
    code: str = Field(..., example="验证码")

# 注册
class RegisterSendCodeSchema(BaseModel):
    email: str = Field(..., example="邮箱")

class RegisterSchema(BaseModel):
    email: str = Field(..., example="邮箱")
    code: str = Field(..., example="验证码")
