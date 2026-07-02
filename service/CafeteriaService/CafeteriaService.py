import random
from datetime import date, timedelta

import requests

from domain.model.CafeteriaMenu import CafeteriaMenu
from extensions import db

# ── 서울 좌표 (Open-Meteo, API 키 필요 없음) ──────────────
SEOUL_LAT = 37.5665
SEOUL_LON = 126.9780

# ── 날씨별 음식 목록 ──────────────────────────────────────
RAINY_FOODS = [
    "순대국", "부대찌개", "짬뽕", "육개장", "감자탕", "매운탕", "알탕",
    "곰탕", "우육면", "마라탕", "마라샹궈", "얼큰수제비", "동태찌개", "홍합탕",
]
HOT_DAY_FOODS = [
    "냉면", "콩국수", "비빔면", "막국수", "물냉면", "초계국수",
    "오이냉국수", "포케볼", "냉모밀", "열무국수",
]
COLD_DAY_FOODS = [
    "갈비탕", "곰탕", "우동", "만둣국", "삼계탕", "육개장",
    "뼈해장국", "도가니탕", "순댓국", "규카츠",
]
NORMAL_FOODS = [
    "김치찌개", "된장찌개", "제육볶음", "돈까스", "비빔밥", "불고기",
    "냉모밀", "볶음밥", "짜장면", "초밥", "회덮밥", "삼겹살", "갈비",
    "닭갈비", "쭈꾸미볶음", "오징어볶음", "청국장", "순두부찌개",
    "마라탕", "마라샹궈", "포케볼", "텐동", "우육면",
    "샐러드 도시락", "그릭요거트볼", "비건 도시락", "밀푀유나베",
    "흑후추두부덮밥", "두부면 파스타", "저당 도시락", "곤약비빔면",
    "단백질 도시락",
]


def _get_seoul_weather() -> dict:
    """Open-Meteo로 서울 오늘 날씨 조회. 실패 시 기본값 반환."""
    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": SEOUL_LAT,
                "longitude": SEOUL_LON,
                "current": "temperature_2m,precipitation",
                "timezone": "Asia/Seoul",
            },
            timeout=5,
        )
        data = resp.json()
        current = data.get("current", {})
        return {
            "temperature": current.get("temperature_2m", 20),
            "precipitation": current.get("precipitation", 0),
        }
    except Exception:
        return {"temperature": 20, "precipitation": 0}


class CafeteriaService:

    # ── 관리자용 CRUD ────────────────────────────────────
    def upsert_menu(self, menu_date: date, menu_text: str, member_id: str) -> CafeteriaMenu:
        menu = CafeteriaMenu.query.filter_by(menu_date=menu_date).first()
        if menu:
            menu.menu_text = menu_text
        else:
            menu = CafeteriaMenu(menu_date=menu_date, menu_text=menu_text, created_by=member_id)
            db.session.add(menu)
        db.session.commit()
        return menu

    def delete_menu(self, menu_date: date) -> bool:
        menu = CafeteriaMenu.query.filter_by(menu_date=menu_date).first()
        if not menu:
            return False
        db.session.delete(menu)
        db.session.commit()
        return True

    # ── 조회 ─────────────────────────────────────────────
    def get_today_menu(self) -> CafeteriaMenu | None:
        return CafeteriaMenu.query.filter_by(menu_date=date.today()).first()

    def get_month_menus(self, year: int, month: int) -> list[CafeteriaMenu]:
        start = date(year, month, 1)
        end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        return (
            CafeteriaMenu.query
            .filter(CafeteriaMenu.menu_date >= start, CafeteriaMenu.menu_date < end)
            .order_by(CafeteriaMenu.menu_date.asc())
            .all()
        )

    # ── 추천 ─────────────────────────────────────────────
    def recommend_lunch(self) -> dict:
        weather = _get_seoul_weather()
        temp = weather["temperature"]
        rain = weather["precipitation"]

        if rain and rain > 0:
            pool = RAINY_FOODS
            reason = "비/눈 오는 날엔 국물이 최고죠"
        elif temp >= 28:
            pool = HOT_DAY_FOODS
            reason = f"오늘 {temp}°C, 시원한 걸로 가시죠"
        elif temp <= 5:
            pool = COLD_DAY_FOODS
            reason = f"오늘 {temp}°C, 뜨끈한 게 땡기네요"
        else:
            pool = NORMAL_FOODS
            reason = "오늘은 무난하게"

        today_menu = self.get_today_menu()
        today_items = set()
        if today_menu:
            today_items = {m.strip() for m in today_menu.menu_text.replace(",", " ").split()}

        candidates = [f for f in pool if f not in today_items]
        if not candidates:
            candidates = pool

        return {
            "recommendation": random.choice(candidates),
            "reason": reason,
            "temperature": temp,
            "precipitation": rain,
        }