from dotenv import load_dotenv
load_dotenv()

import os

from flask import Flask, send_from_directory
from extensions import db, init_extensions
from domain.model.Member import Member
from domain.model.Department import Department
from web.routes.AuthenticationRestController import auth_bp
from web.routes.GroupRestController import group_bp
from web.routes.RBACRestController import rbac_bp
from web.routes.Todo import todo_bp
from web.routes.MemberRestController import member_bp
from web.routes.StorageRestController import storage_bp
from web.routes.VdiRestController import vdi_bp

app = Flask(__name__)
init_extensions(app)

app.register_blueprint(auth_bp)
app.register_blueprint(rbac_bp)
app.register_blueprint(group_bp)
app.register_blueprint(todo_bp)
app.register_blueprint(member_bp)
app.register_blueprint(storage_bp)
app.register_blueprint(vdi_bp)

with app.app_context():
    from domain.model.Member import Member
    from domain.model.RolePermission import role_permission_table
    from domain.model.Role import Role
    from domain.model.Permission import Permission, PermissionResource
    from domain.model.RoleBinding import RoleBinding
    from domain.model.StorageBucket import StorageBucket
    from domain.model.StorageResource import StorageResource
    from domain.model.Vdi import Vdi, VdiSnapshot
    from domain.model.Group import Group, tb_group_member
    from domain.model.Department import Department
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


@app.route('/iam')
def iam_page():
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), 'static', 'pages'),
        'iam.html'
    )

@app.route('/iam/roles')
def rbac_page():
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), 'static', 'pages'),
        'rbac.html'
    )

@app.route('/iam/groups')
def group_page():
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), 'static', 'pages'),
        'group.html'
    )

@app.route('/iam/permissions')
def permission_page():
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), 'static', 'pages'),
        'permission.html'
    )

@app.route('/mypage')
def mypage():
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), 'static', 'pages'),
        'mypage.html'
    )



@app.route('/vdi/list')
def vdi_list_page():
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), 'static', 'pages'),
        'vdi-list.html'
    )

@app.route('/vdi')
def vdi_page():
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), 'static', 'pages'),
        'vdi.html'
    )


@app.route('/objstorage')
def objstorage_page():
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), 'static', 'pages'),
        'objstorage.html'
    )


if __name__ == '__main__':
    app.run(debug=True)
