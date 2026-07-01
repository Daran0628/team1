from dotenv import load_dotenv
load_dotenv()

import os

from flask import Flask, send_from_directory
from extensions import db, init_extensions

from web.routes.AuthenticationRestController import auth_bp
from web.routes.Todo import todo_bp
from web.routes.NoticeController import notice_bp  # ← 추가
from web.routes.FaqController import faq_bp  # ← 추가
from domain.model.Ticket import Ticket  # ← 추가
from web.routes.TicketController import ticket_bp  # ← 추가
from web.routes.RBACRestController import rbac_bp  # ← 추가 (IAM/RBAC)
from web.routes.GroupRestController import group_bp  # ← 추가 (IAM/RBAC)

app = Flask(__name__)
init_extensions(app)

app.register_blueprint(auth_bp)
app.register_blueprint(todo_bp)
app.register_blueprint(notice_bp)  # ← 추가
app.register_blueprint(faq_bp)  # ← 추가
app.register_blueprint(ticket_bp)  # ← 추가
app.register_blueprint(rbac_bp)  # ← 추가 (IAM/RBAC)
app.register_blueprint(group_bp)  # ← 추가 (IAM/RBAC)



with app.app_context():
    from domain.model.Member import Member  # 모델 등록
    from domain.model.Department import Department  # ← 추가 (Member.department_id FK)
    from domain.model.Notice import Notice  # ← 이 줄 추가
    from domain.model.Faq import Faq      # ← 추가
    from domain.model.Group import Group  # ← 추가 (IAM/RBAC)
    from domain.model.Permission import Permission, PermissionResource  # ← 추가 (IAM/RBAC)
    from domain.model.Role import Role  # ← 추가 (IAM/RBAC)
    from domain.model.RoleBinding import RoleBinding  # ← 추가 (IAM/RBAC)
    db.create_all()                         # 없는 테이블만 자동 생성

@app.route('/')
def index():
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), 'static'),
        'index.html'
    )

@app.route('/login')
def login_page():
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), 'static', 'pages'),
        'login.html'
    )

# ── IAM / RBAC 페이지 라우트 ──────────────────────────────
_PAGES_DIR = os.path.join(os.path.dirname(__file__), 'static', 'pages')

@app.route('/iam')
def iam_page():
    return send_from_directory(_PAGES_DIR, 'iam.html')

@app.route('/iam/roles')
def iam_roles_page():
    return send_from_directory(_PAGES_DIR, 'rbac.html')

@app.route('/iam/groups')
def iam_groups_page():
    return send_from_directory(_PAGES_DIR, 'group.html')

@app.route('/iam/permissions')
def iam_permissions_page():
    return send_from_directory(_PAGES_DIR, 'permission.html')

if __name__ == '__main__':
    app.run(debug=True)
