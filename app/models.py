from sqlalchemy import Column, Integer, String, Float, DateTime, func
from app.database import Base

class Birth(Base):
    __tablename__ = "births"

    id = Column(Integer, primary_key=True, index=True)
    geo = Column(String, nullable=False)
    geo_object = Column(String, nullable=False)
    time_period = Column(Integer, nullable=False)
    obs_value = Column(Float, nullable=False)

class Family(Base):
    __tablename__ = "families"

    id = Column(Integer, primary_key=True, autoincrement=True)
    geo_code = Column(String(10), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    total_households = Column(Float, nullable=True)
    single_men = Column(Float, nullable=True)
    single_women = Column(Float, nullable=True)
    couples_with_children = Column(Float, nullable=True)
    single_parent_families = Column(Float, nullable=True)
    single_fathers = Column(Float, nullable=True)
    single_mothers = Column(Float, nullable=True)
    couples_without_children = Column(Float, nullable=True)
    large_families = Column(Float, nullable=True)
    children_under_24_no_sibling = Column(Float, nullable=True)
    children_under_24_one_sibling = Column(Float, nullable=True)
    children_under_24_two_siblings = Column(Float, nullable=True)
    children_under_24_three_siblings = Column(Float, nullable=True)
    children_under_24_four_or_more_siblings = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class GeoCode(Base):
    __tablename__ = "geo_codes"

    codgeo = Column(String(10), primary_key=True, index=True)  # Code commune
    libgeo = Column(String, nullable=False)  # Nom de la commune
    epci = Column(String(20), nullable=True)  # Code EPCI
    libepci = Column(String, nullable=True)  # Nom de l'EPCI
    dep = Column(String(5), nullable=False)  # Département
    reg = Column(String(5), nullable=False)  # Région

