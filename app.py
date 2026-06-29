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

app = Flask(__name__)
init_extensions(app)

app.register_blueprint(auth_bp)
app.register_blueprint(todo_bp)
app.register_blueprint(notice_bp)  # ← 추가
app.register_blueprint(faq_bp)  # ← 추가
app.register_blueprint(ticket_bp)  # ← 추가



with app.app_context():
    from domain.model.Member import Member  # 모델 등록
    from domain.model.Notice import Notice  # ← 이 줄 추가
    from domain.model.Faq import Faq      # ← 추가
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

if __name__ == '__main__':
    app.run(debug=True)
