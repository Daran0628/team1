from dataclasses import dataclass, field


@dataclass
class MenuItemResponseDTO:
    menu_date: str
    menu_text: str


@dataclass
class MonthMenuResponseDTO:
    year: int
    month: int
    items: list = field(default_factory=list)


@dataclass
class LunchRecommendResponseDTO:
    recommendation: str
    reason: str
    temperature: float
    precipitation: float
