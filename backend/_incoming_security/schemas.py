from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    username: str
    email: EmailStr
    comment: str | None = None  # 👈 campo opcional

class UserCreate(UserBase):
    password: str  # si ya lo tenías

class User(UserBase):
    id: int

    class Config:
        orm_mode = True
