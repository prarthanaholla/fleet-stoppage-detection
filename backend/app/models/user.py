from sqlalchemy import Column, Integer, String
from app.db.base import Base

class User(Base):
    __tablename__="users"

    id=Column(Integer,primary_key=True)
    name=Column(String(100),nullable=False)
    email=Column(String(150),unique=True,nullable=False)
    password_hash=Column(String(255),nullable=False)
