from extensions import db

# tb_role ↔ tb_permission 순수 중간 테이블
role_permission_table = db.Table(
    "tb_role_permission",
    db.Column("role_id",       db.String(36), db.ForeignKey("tb_role.role_id"),             primary_key=True),
    db.Column("permission_id", db.String(36), db.ForeignKey("tb_permission.permission_id"), primary_key=True),
)
