from pydantic import BaseModel, Field

class SendOTPRequest(BaseModel):
    mobile_number: str = Field(..., min_length=10, max_length=15)

class VerifyOTPRequest(BaseModel):
    mobile_number: str
    otp: str = Field(..., min_length=4, max_length=6)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SignupInitRequest(BaseModel):
    phone: str
    first_name: str
    last_name: str

class SignupVerifyRequest(BaseModel):
    phone: str
    otp: str

class SignupResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
