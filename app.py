from dotenv import load_dotenv
load_dotenv()

import os

from flask import Flask, send_from_directory
from flask_sse import sse
from extensions import db, init_extensions
from core.config.RedisConfig import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWD
from domain.model.Member import Member
from domain.model.Department import Department
from web.routes.AuthenticationRestController import auth_bp
from web.routes.GroupRestController import group_bp
from web.routes.RBACRestController import rbac_bp
from web.routes.Todo import todo_bp
from web.routes.MemberRestController import member_bp
from web.routes.StorageRestController import storage_bp
from web.routes.VdiRestController import vdi_bp
from web.routes.ChatRestController import chat_bp
from service.ChatService.ChatService import ensure_chat_bucket
from web.routes.MailRestController import mail_bp
from web.routes.CodingTestRestController import coding_test_bp

app = Flask(__name__)
init_extensions(app)

_redis_pw = f":{REDIS_PASSWD}@" if REDIS_PASSWD else ""
app.config["REDIS_URL"] = f"redis://{_redis_pw}{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

app.register_blueprint(auth_bp)
app.register_blueprint(rbac_bp)
app.register_blueprint(group_bp)
app.register_blueprint(todo_bp)
app.register_blueprint(member_bp)
app.register_blueprint(storage_bp)
app.register_blueprint(vdi_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(sse, url_prefix="/stream")
app.register_blueprint(mail_bp)
app.register_blueprint(coding_test_bp)

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
    from domain.model.ChatRoom import ChatRoom, ChatRoomMember
    from domain.model.ChatMessage import ChatMessage
    from domain.model.ChatFile import ChatFile
    from domain.model.Problem import Problem
    from domain.model.TestCase import TestCase
    from domain.model.Submission import Submission
    from domain.model.Score import Score
    db.create_all()
    ensure_chat_bucket()

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

@app.route('/person')
def person_page():
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), 'static', 'pages'),
        'person.html'
    )

@app.route('/mypage')
def mypage():
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), 'static', 'pages'),
        'mypage.html'
    )


@app.route('/coding-test')
def coding_test_page():
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), 'static', 'pages'),
        'codingtest.html'
    )

@app.route('/coding-test/<problem_id>')
def coding_test_detail_page(problem_id):
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), 'static', 'pages'),
        'codingtest-detail.html'
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


@app.route('/mail')
def mail_page():
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), 'static', 'pages'),
        'mail.html'
    )

@app.route('/objstorage')
def objstorage_page():
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), 'static', 'pages'),
        'objstorage.html'
    )


@app.route('/chat')
def chat_page():
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), 'static', 'pages'),
        'chat.html'
    )


@app.route('/chat/<room_id>')
def chatroom_page(room_id):
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), 'static', 'pages'),
        'chatroom.html'
    )


if __name__ == '__main__':
    app.run(debug=True, threaded=True)
