from pydantic import BaseModel, field_validator

class RegisterSchema(BaseModel):
    name: str
    email: str
    password: str
    org_name: str

    @field_validator("password")
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

class LoginSchema(BaseModel):
    email: str
    password: str