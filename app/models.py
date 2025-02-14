from sqlalchemy import Column, Integer, String, Float
from app.database import Base  # Vérifie cet import

class Birth(Base):
    __tablename__ = "births"

    id = Column(Integer, primary_key=True, index=True)
    geo = Column(String, nullable=False)
    geo_object = Column(String, nullable=False)
    time_period = Column(Integer, nullable=False)
    obs_value = Column(Float, nullable=False)
