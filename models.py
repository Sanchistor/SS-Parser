from sqlalchemy import Column, Integer, String, Boolean, Float, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Apartment(Base):
    __tablename__ = "apartments"

    id = Column(Integer, primary_key=True)
    external_id = Column(String, unique=True)

    price = Column(Integer)
    floor = Column(Integer)

    lat = Column(Float)
    lon = Column(Float)
    distance = Column(Float)

    description = Column(Text)

    url = Column(String)
    approved = Column(Boolean, default=False)
