from sqlalchemy import Column, Integer, String, ForeignKey, CheckConstraint, UniqueConstraint
from app.db.base import Base

class OrgUser(Base):
    __tablename__ = "org_users"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    org_id = Column(Integer, ForeignKey("organisations.id"), nullable=False)
    role = Column(String(20), nullable=False, default="member")

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'manager', 'member')", name="valid_role"),
        UniqueConstraint("user_id", "org_id", name="unique_user_org"),
    )