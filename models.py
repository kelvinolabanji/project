from sqlalchemy import Column, String, Boolean, Integer
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)  # Password column fixed
    role = Column(String, default="customer")
    is_verified = Column(Boolean, default=False)
