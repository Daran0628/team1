from dotenv import load_dotenv
load_dotenv()

import os
import sys

# redis/ 폴더를 패키지로 만들면 PyPI redis 패키지와 충돌하므로,
# 디렉토리 자체를 sys.path에 추가해 redis_client를 직접 임포트함
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'redis'))

from flask import Flask, send_from_directory
from auth.extensions import init_extensions
from routes.todo import todo_bp
from auth.routes import auth_bp

app = Flask(__name__)
init_extensions(app)

# ── Blueprint 등록 ────────────────────────────
app.register_blueprint(todo_bp)
app.register_blueprint(auth_bp)

# ── 정적 파일 서빙 (index.html) ───────────────
@app.route('/')
def index():
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), 'static'),
        'index.html'
    )

if __name__ == '__main__':
    app.run(debug=True)
