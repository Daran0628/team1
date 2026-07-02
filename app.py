from dotenv import load_dotenv
load_dotenv()

import os

from flask import Flask, send_from_directory
from flask_sse import sse
from extensions import db, init_extensions

from core.config.RedisConfig import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWD
from web.routes.AuthenticationRestController import auth_bp
from web.routes.GroupRestController import group_bp
from web.routes.RBACRestController import rbac_bp
from web.routes.Todo import todo_bp
from web.routes.NoticeController import notice_bp
from web.routes.FaqController import faq_bp
from web.routes.TicketController import ticket_bp
from web.routes.MailRestController import mail_bp
from web.routes.ChatRestController import chat_bp
from service.ChatService.ChatService import ensure_chat_bucket
from web.routes.StorageRestController import storage_bp
from web.routes.MemberRestController import member_bp
from web.routes.VdiRestController import vdi_bp
from web.routes.BoardRestController import board_bp
from service.BoardService.BoardService import ensure_board_bucket
from web.routes.CafeteriaRestController import cafeteria_bp

app = Flask(__name__)
init_extensions(app)
_redis_pw = f":{REDIS_PASSWD}@" if REDIS_PASSWD else ""
app.config["REDIS_URL"] = f"redis://{_redis_pw}{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

app.register_blueprint(auth_bp)
app.register_blueprint(rbac_bp)
app.register_blueprint(group_bp)
app.register_blueprint(todo_bp)
app.register_blueprint(notice_bp)
app.register_blueprint(faq_bp)
app.register_blueprint(ticket_bp)
app.register_blueprint(mail_bp)
app.register_blueprint(storage_bp)
app.register_blueprint(member_bp)
app.register_blueprint(vdi_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(sse, url_prefix="/stream")
app.register_blueprint(board_bp)
app.register_blueprint(cafeteria_bp)


with app.app_context():
    from domain.model.Member import Member
    from domain.model.Department import Department
    from domain.model.Notice import Notice
    from domain.model.Faq import Faq
    from domain.model.Ticket import Ticket
    from domain.model.Group import Group, tb_group_member
    from domain.model.Permission import Permission, PermissionResource
    from domain.model.Role import Role
    from domain.model.RoleBinding import RoleBinding
    from domain.model.RolePermission import role_permission_table
    from domain.model.StorageBucket import StorageBucket
    from domain.model.StorageResource import StorageResource
    from domain.model.Vdi import Vdi, VdiSnapshot
    from domain.model.ChatRoom import ChatRoom, ChatRoomMember
    from domain.model.ChatMessage import ChatMessage
    from domain.model.ChatFile import ChatFile
    from domain.model.Board import Board, Post, PostAttachment, PostComment, PostLike, PostView, BoardApprover
    from domain.model.CafeteriaMenu import CafeteriaMenu
    db.create_all()
    ensure_chat_bucket()
    ensure_board_bucket()


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

@app.route('/person')
def person_page():
    return send_from_directory(_PAGES_DIR, 'person.html')

@app.route('/mypage')
def mypage():
    return send_from_directory(_PAGES_DIR, 'mypage.html')

@app.route('/mail')
def mail_page():
    return send_from_directory(_PAGES_DIR, 'mail.html')

@app.route('/objstorage')
def objstorage_page():
    return send_from_directory(_PAGES_DIR, 'objstorage.html')

@app.route('/vdi/list')
def vdi_list_page():
    return send_from_directory(_PAGES_DIR, 'vdi-list.html')

@app.route('/vdi')
def vdi_page():
    return send_from_directory(_PAGES_DIR, 'vdi.html')

@app.route('/chat')
def chat_page():
    return send_from_directory(_PAGES_DIR, 'chat.html')

@app.route('/chat/<room_id>')
def chatroom_page(room_id):
    return send_from_directory(_PAGES_DIR, 'chatroom.html')

@app.route('/board')
def board_page():
    return send_from_directory(_PAGES_DIR, 'board.html')

@app.route('/board/<string:board_name>/post/<string:post_id>')
def board_post_page(board_name, post_id):
    return send_from_directory(_PAGES_DIR, 'board-post.html')

@app.route('/board/<string:board_name>')
def board_posts_page(board_name):
    return send_from_directory(_PAGES_DIR, 'board-posts.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
