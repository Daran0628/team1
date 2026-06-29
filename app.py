from dotenv import load_dotenv
load_dotenv()

import os

from flask import Flask, send_from_directory
from extensions import db, init_extensions
from web.routes.AuthenticationRestController import auth_bp
from web.routes.Todo import todo_bp

app = Flask(__name__)
init_extensions(app)

app.register_blueprint(auth_bp)
app.register_blueprint(todo_bp)

with app.app_context():
    from domain.model.Member import Member
    from domain.model.RolePermission import role_permission_table
    from domain.model.Role import Role
    from domain.model.Permission import Permission
    from domain.model.RoleBinding import RoleBinding
    from domain.model.StorageResource import StorageResource
    db.create_all()

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
