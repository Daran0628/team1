from domain.model.CafeteriaMenu import CafeteriaMenu
from web.dto.CafeteriaResponseDTO import (
    MenuItemResponseDTO,
    MonthMenuResponseDTO,
    LunchRecommendResponseDTO,
)


class CafeteriaConverter:

    @staticmethod
    def to_menu_item_dto(menu: CafeteriaMenu) -> MenuItemResponseDTO:
        return MenuItemResponseDTO(
            menu_date=menu.menu_date.isoformat(),
            menu_text=menu.menu_text,
        )

    @staticmethod
    def to_month_dto(year: int, month: int, menus: list) -> MonthMenuResponseDTO:
        items = [CafeteriaConverter.to_menu_item_dto(m) for m in menus]
        return MonthMenuResponseDTO(year=year, month=month, items=items)

    @staticmethod
    def to_recommend_dto(result: dict) -> LunchRecommendResponseDTO:
        return LunchRecommendResponseDTO(
            recommendation=result["recommendation"],
            reason=result["reason"],
            temperature=result["temperature"],
            precipitation=result["precipitation"],
        )
