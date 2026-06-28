from sqlalchemy import Column, Integer, String
from app.db.base import Base

class Organisation(Base):
    __tablename__="organisations"

    id=Column(Integer,primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
