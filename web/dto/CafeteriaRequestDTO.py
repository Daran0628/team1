from dataclasses import dataclass


@dataclass
class UpsertMenuRequestDTO:
    menu_date: str   # "2026-07-02" 형식
    menu_text: str
