import uuid
from extensions import db


class CafeteriaMenu(db.Model):
    __tablename__ = "tb_cafeteria_menu"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    menu_date = db.Column(db.Date, nullable=False, unique=True)
    menu_text = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.String(36), db.ForeignKey("tb_members.member_id"), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    def __repr__(self):
        return f"<CafeteriaMenu {self.menu_date} {self.menu_text[:20]}>"