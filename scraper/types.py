from dataclasses import dataclass

@dataclass
class ApartmentDTO:
    external_id: str
    lat: float
    lon: float
    address: str
    price: int
    rooms: int
    floor: int
    total_floors: int
    url: str
