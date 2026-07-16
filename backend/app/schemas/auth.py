from pydantic import BaseModel

class RegisterSchema(BaseModel):
    name: str
    email: str
    password: str
    org_name: str

class LoginSchema(BaseModel):
    email: str
    password: str
