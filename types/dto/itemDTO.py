from dataclasses import dataclass


@dataclass
class ItemDTO:
    category: str
    subcategory: str
    private_data: str
    price: float
    description: str
