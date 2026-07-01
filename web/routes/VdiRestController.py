# import fcntl
# import json
# import os
# import pty
# import select
# import struct
# import subprocess
# import termios
# import threading

# from flask import Blueprint, request
# from flask_jwt_extended import jwt_required, get_jwt_identity, decode_token

# from core.rbac.RBACUtils import vdi_required, check_vdi_action
# from core.response.ApiResponse import ApiResponse
# from core.response.ErrorStatus import ErrorStatus
# from core.response.SuccessStatus import SuccessStatus
# from domain.model.Member import Member
# from domain.model.Vdi import Vdi
# from extensions import sock
# from service.VdiService.VdiService import (
#     VdiException,
#     create_vdi,
#     list_vdi,
#     get_vdi,
#     start_vdi,
#     stop_vdi,
#     reboot_vdi,
#     delete_vdi,
#     create_snapshot,
#     list_snapshots,
# )

# vdi_bp = Blueprint('vdi', __name__, url_prefix='/api/vdi')


# def _current_member() -> Member | None:
#     return Member.query.filter_by(account_id=get_jwt_identity()).first()


# def _handle(fn):
#     try:
#         return fn()
#     except VdiException as e:
#         return ApiResponse.on_failure(e.error_status, e.detail)
#     except ValueError as e:
#         return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, str(e))
#     except Exception as e:
#         return ApiResponse.on_failure(ErrorStatus._INTERNAL_SERVER_ERROR, str(e))


# # ── 인스턴스 CRUD ─────────────────────────────────────────────

# @vdi_bp.route('/instances', methods=['POST'])
# @jwt_required()
# @vdi_required('MANAGE')
# def api_create_vdi():
#     body = request.get_json(silent=True) or {}
#     def work():
#         container_name = body.get('containerName', '').strip()
#         image          = body.get('image', '').strip()
#         target_member  = body.get('assignedTo', '').strip()  # member_id

#         if not container_name or not image or not target_member:
#             return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, "containerName, image, assignedTo 필드가 필요합니다.")

#         result = create_vdi(container_name, image, target_member)
#         return ApiResponse.on_success(SuccessStatus.VDI_CREATE, result)
#     return _handle(work)


# @vdi_bp.route('/instances', methods=['GET'])
# @jwt_required()
# @vdi_required('MANAGE')
# def api_list_all_vdi():
#     def work():
#         result = list_vdi()
#         return ApiResponse.on_success(SuccessStatus.VDI_READ, result)
#     return _handle(work)


# @vdi_bp.route('/instances/me', methods=['GET'])
# @jwt_required()
# def api_list_my_vdi():
#     def work():
#         member = _current_member()
#         if not member:
#             return ApiResponse.on_failure(ErrorStatus.MEMBER_NOT_FOUND)
#         result = list_vdi(member_id=member.id)
#         return ApiResponse.on_success(SuccessStatus.VDI_READ, result)
#     return _handle(work)


# @vdi_bp.route('/instances/<vdi_id>', methods=['GET'])
# @jwt_required()
# @vdi_required('CONNECT')
# def api_get_vdi(vdi_id: str):
#     def work():
#         result = get_vdi(vdi_id)
#         return ApiResponse.on_success(SuccessStatus.VDI_READ, result)
#     return _handle(work)


# @vdi_bp.route('/instances/<vdi_id>', methods=['DELETE'])
# @jwt_required()
# @vdi_required('MANAGE')
# def api_delete_vdi(vdi_id: str):
#     def work():
#         delete_vdi(vdi_id)
#         return ApiResponse.on_success(SuccessStatus.VDI_DELETE)
#     return _handle(work)


# # ── 전원 제어 ─────────────────────────────────────────────────

# @vdi_bp.route('/instances/<vdi_id>/start', methods=['POST'])
# @jwt_required()
# @vdi_required('POWER_ON')
# def api_start_vdi(vdi_id: str):
#     def work():
#         result = start_vdi(vdi_id)
#         return ApiResponse.on_success(SuccessStatus.VDI_START, result)
#     return _handle(work)


# @vdi_bp.route('/instances/<vdi_id>/stop', methods=['POST'])
# @jwt_required()
# @vdi_required('POWER_OFF')
# def api_stop_vdi(vdi_id: str):
#     def work():
#         result = stop_vdi(vdi_id)
#         return ApiResponse.on_success(SuccessStatus.VDI_STOP, result)
#     return _handle(work)


# @vdi_bp.route('/instances/<vdi_id>/reboot', methods=['POST'])
# @jwt_required()
# @vdi_required('REBOOT')
# def api_reboot_vdi(vdi_id: str):
#     def work():
#         result = reboot_vdi(vdi_id)
#         return ApiResponse.on_success(SuccessStatus.VDI_REBOOT, result)
#     return _handle(work)


# # ── 스냅샷 ────────────────────────────────────────────────────

# @vdi_bp.route('/instances/<vdi_id>/snapshots', methods=['POST'])
# @jwt_required()
# @vdi_required('SNAPSHOT')
# def api_create_snapshot(vdi_id: str):
#     body = request.get_json(silent=True) or {}
#     def work():
#         name = body.get('snapshotName', '').strip()
#         if not name:
#             return ApiResponse.on_failure(ErrorStatus._BAD_REQUEST, "snapshotName 필드가 필요합니다.")
#         member = _current_member()
#         result = create_snapshot(vdi_id, name, member.id if member else '')
#         return ApiResponse.on_success(SuccessStatus.VDI_SNAPSHOT_CREATE, result)
#     return _handle(work)


# @vdi_bp.route('/instances/<vdi_id>/snapshots', methods=['GET'])
# @jwt_required()
# @vdi_required('CONNECT')
# def api_list_snapshots(vdi_id: str):
#     def work():
#         result = list_snapshots(vdi_id)
#         return ApiResponse.on_success(SuccessStatus.VDI_SNAPSHOT_READ, result)
#     return _handle(work)


# # ── WebSocket 터미널 ──────────────────────────────────────────
# # URL: ws://<host>/api/vdi/instances/<vdi_id>/terminal?token=<jwt>
# # xterm.js → WS → PTY → docker exec -it <container> /bin/bash
# # resize:  {"type":"resize","cols":120,"rows":30}

# @sock.route('/api/vdi/instances/<vdi_id>/terminal')
# def vdi_terminal(ws, vdi_id: str):
#     # 1. JWT 검증 (쿼리 파라미터 노출 방지 → 연결 후 첫 메시지로 수신)
#     import json as _json
#     try:
#         auth_msg = ws.receive(timeout=10)
#         auth_data = _json.loads(auth_msg)
#         if auth_data.get('type') != 'auth':
#             raise ValueError('expected auth message')
#         token = auth_data.get('token', '')
#         decoded = decode_token(token)
#         account_id = decoded['sub']
#     except Exception:
#         ws.close(1008, 'Unauthorized')
#         return

#     # 2. VDI 조회
#     vdi = Vdi.query.get(vdi_id)
#     if not vdi:
#         ws.close(1008, 'VDI not found')
#         return

#     # 3. RBAC 확인 (CONNECT 액션)
#     from flask_jwt_extended import create_access_token
#     # JWT 컨텍스트 없이 check_vdi_action을 호출하기 위해 직접 조회
#     from domain.model.Member import Member as MemberModel
#     from domain.model.RoleBinding import RoleBinding
#     from domain.enum.SubjectType import SubjectType

#     member = MemberModel.query.filter_by(account_id=account_id).first()
#     if not member:
#         ws.close(1008, 'Member not found')
#         return

#     role_claim = decoded.get('role', '')
#     _ADMIN_TYPES = {'ADMIN', 'SUPERADMIN'}
#     allowed = role_claim in _ADMIN_TYPES

#     if not allowed and str(member.id) == str(vdi.assigned_to):
#         allowed = True  # 자신의 VDI는 CONNECT 자동 허용

#     if not allowed:
#         direct = RoleBinding.query.filter_by(subject_type=SubjectType.MEMBER, subject_id=member.id).all()
#         group_ids = [g.id for g in member.groups]
#         group_bindings = RoleBinding.query.filter(
#             RoleBinding.subject_type == SubjectType.TEAM,
#             RoleBinding.subject_id.in_(group_ids),
#         ).all() if group_ids else []

#         for binding in direct + group_bindings:
#             for perm in binding.role.permissions:
#                 if perm.perm_type == 'VDI' and (
#                     'CONNECT' in perm.action_list or 'MANAGE' in perm.action_list
#                 ):
#                     allowed = True
#                     break
#             if allowed:
#                 break

#     if not allowed:
#         ws.close(1008, 'Forbidden')
#         return

#     if vdi.status != 'RUNNING':
#         ws.send('\r\n[VDI가 실행 중이 아닙니다. 먼저 시작해주세요.]\r\n')
#         ws.close(1000, 'VDI not running')
#         return

#     # 4. PTY 생성 + docker exec 실행
#     master_fd, slave_fd = pty.openpty()
#     try:
#         proc = subprocess.Popen(
#             ['docker', 'exec', '-it', vdi.container_name, '/bin/bash'],
#             stdin=slave_fd,
#             stdout=slave_fd,
#             stderr=slave_fd,
#             close_fds=True,
#         )
#     except FileNotFoundError:
#         ws.send('\r\n[docker 명령어를 찾을 수 없습니다.]\r\n')
#         os.close(master_fd)
#         os.close(slave_fd)
#         return

#     os.close(slave_fd)

#     # 5. PTY → WS 스트리밍 (별도 스레드)
#     stop_event = threading.Event()

#     def _pty_to_ws():
#         while not stop_event.is_set():
#             try:
#                 r, _, _ = select.select([master_fd], [], [], 0.1)
#                 if r:
#                     data = os.read(master_fd, 4096)
#                     if not data:
#                         break
#                     ws.send(data.decode('utf-8', errors='replace'))
#             except OSError:
#                 break

#     reader = threading.Thread(target=_pty_to_ws, daemon=True)
#     reader.start()

#     # 6. WS → PTY 스트리밍 (메인 루프)
#     try:
#         while True:
#             msg = ws.receive()
#             if msg is None:
#                 break
#             # resize 메시지 처리
#             try:
#                 parsed = json.loads(msg)
#                 if parsed.get('type') == 'resize':
#                     rows = int(parsed.get('rows', 24))
#                     cols = int(parsed.get('cols', 80))
#                     winsize = struct.pack('HHHH', rows, cols, 0, 0)
#                     fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
#                     continue
#             except (json.JSONDecodeError, KeyError, ValueError, OSError):
#                 pass
#             # 일반 입력 → PTY stdin
#             try:
#                 payload = msg.encode() if isinstance(msg, str) else msg
#                 os.write(master_fd, payload)
#             except OSError:
#                 break
#     except Exception:
#         pass
#     finally:
#         stop_event.set()
#         try:
#             proc.terminate()
#         except Exception:
#             pass
#         try:
#             os.close(master_fd)
#         except OSError:
#             pass
