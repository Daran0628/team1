import io
import logging
import uuid
from datetime import datetime, timedelta, timezone

from flask_sse import sse
from minio import S3Error

from core.config.MinioConfig import get_minio_client
from extensions import db
from domain.enum.ChatRoomType import ChatRoomType
from domain.enum.ChatRoomRole import ChatRoomRole
from domain.enum.ChatMessageType import ChatMessageType
from domain.model.ChatFile import ChatFile
from domain.model.ChatRoom import ChatRoom, ChatRoomMember
from domain.model.ChatMessage import ChatMessage
from domain.model.Member import Member
from domain.model.StorageBucket import StorageBucket
from domain.model.StorageResource import StorageResource
from web.dto.ChatRequestDTO import CreateRoomRequestDTO, SendMessageRequestDTO, AddRoomMembersRequestDTO
from web.dto.ChatResponseDTO import (
    ChatFileResponseDTO,
    ChatRoomResponseDTO,
    ChatMessageResponseDTO,
    RoomMemberDTO,
)

logger = logging.getLogger(__name__)

CHAT_BUCKET = "chat-files"
MAX_FILE_SIZE = 25 * 1024 * 1024  # 채팅 첨부파일 파일당 최대 25MB

_MSG_TYPE_MAP = {
    "TEXT":   ChatMessageType.Text,
    "FILE":   ChatMessageType.File,
    "IMAGE":  ChatMessageType.Image,
    "NOTICE": ChatMessageType.Notice,
}


def ensure_chat_bucket() -> None:
    client = get_minio_client()
    if not StorageBucket.query.filter_by(bucket_name=CHAT_BUCKET).first():
        try:
            if not client.bucket_exists(CHAT_BUCKET):
                client.make_bucket(CHAT_BUCKET)
        except S3Error as e:
            logger.error("chat-files 버킷 생성 실패: %s", e)
            return
        db.session.add(StorageBucket(bucket_name=CHAT_BUCKET, created_by="system"))
        db.session.commit()
        logger.info("chat-files 버킷 생성 완료")


def _to_file_dto(f: ChatFile) -> ChatFileResponseDTO:
    return ChatFileResponseDTO(
        file_id=f.id,
        original_name=f.original_name,
        file_size=f.file_size,
        mime_type=f.mime_type,
        created_at=f.created_at.isoformat(),
    )


def _to_room_member_dto(membership: ChatRoomMember) -> RoomMemberDTO:
    m: Member = membership.member
    return RoomMemberDTO(
        member_id=membership.member_id,
        account_id=m.account_id,
        name_ko=m.name_ko,
        room_role=membership.room_role.value,
        joined_at=membership.joined_at.isoformat(),
        last_read_at=membership.last_read_at.isoformat() if membership.last_read_at else None,
    )


def _to_room_dto(room: ChatRoom, membership: ChatRoomMember = None) -> ChatRoomResponseDTO:
    active_members = [ms for ms in room.members if ms.is_active]

    unread_count = 0
    if membership:
        cutoff = membership.last_read_at or membership.joined_at
        unread_count = ChatMessage.query.filter(
            ChatMessage.room_id == room.id,
            ChatMessage.created_at > cutoff,
            ChatMessage.is_deleted == False,
        ).count()

    last_msg = (
        ChatMessage.query
        .filter_by(room_id=room.id, is_deleted=False)
        .order_by(ChatMessage.created_at.desc())
        .first()
    )
    last_message_at = last_msg.created_at.isoformat() if last_msg else None

    return ChatRoomResponseDTO(
        room_id=room.id,
        room_type=room.room_type.value,
        room_name=room.room_name,
        created_by=room.created_by,
        created_at=room.created_at.isoformat(),
        members=[_to_room_member_dto(ms) for ms in active_members],
        unread_count=unread_count,
        last_message_at=last_message_at,
    )


def _to_message_dto(msg: ChatMessage) -> ChatMessageResponseDTO:
    sender: Member = msg.sender
    return ChatMessageResponseDTO(
        message_id=msg.id,
        room_id=msg.room_id,
        sender_id=msg.sender_id,
        sender_name=sender.name_ko if sender else "",
        message_type=msg.message_type.value,
        content=msg.content,
        is_deleted=msg.is_deleted,
        created_at=msg.created_at.isoformat(),
        files=[_to_file_dto(f) for f in msg.files],
    )


class ChatService:

    # ── 방 생성 ─────────────────────────────────────────────────

    def create_room(self, creator_id: str, dto: CreateRoomRequestDTO) -> ChatRoomResponseDTO:
        room_type = ChatRoomType.Direct if dto.room_type == "DIRECT" else ChatRoomType.Group

        if room_type == ChatRoomType.Direct:
            other_id = dto.member_ids[0]
            direct_key = "_".join(sorted([creator_id, other_id]))
            if ChatRoom.query.filter_by(direct_key=direct_key).first():
                raise ValueError("CHAT_DIRECT_ALREADY_EXISTS")
            room = ChatRoom(room_type=room_type, created_by=creator_id, direct_key=direct_key)
            participant_ids = [creator_id, other_id]
        else:
            room = ChatRoom(room_type=room_type, room_name=dto.room_name, created_by=creator_id)
            participant_ids = [creator_id] + dto.member_ids

        members = Member.query.filter(Member.id.in_(participant_ids)).all()
        if len(members) != len(participant_ids):
            raise ValueError("CHAT_NOT_A_MEMBER")

        db.session.add(room)
        db.session.flush()

        for member in members:
            role = ChatRoomRole.Admin if member.id == creator_id else ChatRoomRole.Member
            db.session.add(ChatRoomMember(room_id=room.id, member_id=member.id, room_role=role))

        db.session.commit()
        logger.info("chat room created: %s by %s", room.id, creator_id)
        return _to_room_dto(room)

    # ── 방 조회 ─────────────────────────────────────────────────

    def get_my_rooms(self, member_id: str) -> list:
        memberships = (
            ChatRoomMember.query
            .filter_by(member_id=member_id, is_active=True)
            .all()
        )
        dtos = [_to_room_dto(ms.room, ms) for ms in memberships]
        return sorted(dtos, key=lambda d: d.last_message_at or d.created_at, reverse=True)

    def get_room(self, room_id: str, member_id: str) -> ChatRoomResponseDTO:
        room = ChatRoom.query.get(room_id)
        if not room:
            raise ValueError("CHAT_ROOM_NOT_FOUND")
        self._assert_member(room_id, member_id)
        return _to_room_dto(room)

    # ── 방 나가기 ────────────────────────────────────────────────

    def leave_room(self, room_id: str, member_id: str, new_admin_id: str = None) -> None:
        room = ChatRoom.query.get(room_id)
        if not room:
            raise ValueError("CHAT_ROOM_NOT_FOUND")

        ms = self._get_membership(room_id, member_id)
        leaver_name = ms.member.name_ko

        if room.room_type == ChatRoomType.Group and ms.room_role == ChatRoomRole.Admin:
            other_active = [m for m in room.members if m.is_active and m.member_id != member_id]
            if other_active:
                if new_admin_id is None:
                    raise ValueError("CHAT_ADMIN_MUST_TRANSFER")
                new_ms = self._get_membership(room_id, new_admin_id)
                new_admin_name = new_ms.member.name_ko
                new_ms.room_role = ChatRoomRole.Admin
                ms.room_role = ChatRoomRole.Member
                ms.is_active = False
                db.session.commit()
                self._publish_notice(
                    room_id, member_id,
                    f"{leaver_name}님이 {new_admin_name}님에게 관리자를 이양하고 채팅방에 나갔습니다."
                )
                logger.info("admin %s transferred to %s and left room %s", member_id, new_admin_id, room_id)
                return

        ms.is_active = False
        db.session.commit()
        self._publish_notice(room_id, member_id, f"{leaver_name}님이 채팅방에 나갔습니다.")
        logger.info("member %s left room %s", member_id, room_id)

    # ── 멤버 관리 ────────────────────────────────────────────────

    def add_members(self, room_id: str, requester_id: str, dto: AddRoomMembersRequestDTO) -> ChatRoomResponseDTO:
        room = ChatRoom.query.get(room_id)
        if not room:
            raise ValueError("CHAT_ROOM_NOT_FOUND")
        self._assert_admin(room_id, requester_id)

        existing_ids = {ms.member_id for ms in room.members if ms.is_active}
        new_members = Member.query.filter(Member.id.in_(dto.member_ids)).all()
        if len(new_members) != len(dto.member_ids):
            raise ValueError("CHAT_NOT_A_MEMBER")

        for member in new_members:
            if member.id in existing_ids:
                raise ValueError("CHAT_ALREADY_A_MEMBER")
            inactive = ChatRoomMember.query.filter_by(room_id=room_id, member_id=member.id).first()
            if inactive:
                inactive.is_active = True
                inactive.room_role = ChatRoomRole.Member  # 재초대 시 항상 일반 멤버로 리셋
            else:
                db.session.add(ChatRoomMember(room_id=room_id, member_id=member.id))

        db.session.commit()

        for member in new_members:
            self._publish_notice(room_id, requester_id, f"{member.name_ko}님이 채팅방에 초대되었습니다.")

        return _to_room_dto(room)

    def remove_member(self, room_id: str, requester_id: str, target_id: str) -> ChatRoomResponseDTO:
        room = ChatRoom.query.get(room_id)
        if not room:
            raise ValueError("CHAT_ROOM_NOT_FOUND")
        if requester_id != target_id:
            self._assert_admin(room_id, requester_id)
        ms = self._get_membership(room_id, target_id)
        name = ms.member.name_ko
        ms.is_active = False
        db.session.commit()
        self._publish_notice(room_id, requester_id, f"{name}님이 채팅방에서 추방되었습니다.")
        return _to_room_dto(room)

    # ── 텍스트 메시지 ────────────────────────────────────────────

    def send_message(self, room_id: str, sender_id: str, dto: SendMessageRequestDTO) -> ChatMessageResponseDTO:
        if not ChatRoom.query.get(room_id):
            raise ValueError("CHAT_ROOM_NOT_FOUND")
        self._assert_member(room_id, sender_id)

        msg = ChatMessage(
            room_id=room_id,
            sender_id=sender_id,
            message_type=_MSG_TYPE_MAP[dto.message_type],
            content=dto.content,
        )
        db.session.add(msg)
        db.session.commit()

        dto_result = _to_message_dto(msg)
        sse.publish(
            {
                "messageId":   dto_result.message_id,
                "roomId":      dto_result.room_id,
                "senderId":    dto_result.sender_id,
                "senderName":  dto_result.sender_name,
                "messageType": dto_result.message_type,
                "content":     dto_result.content,
                "createdAt":   dto_result.created_at,
            },
            type="message",
            channel=f"room:{room_id}",
        )
        return dto_result

    def get_messages(self, room_id: str, member_id: str, since: str = None, limit: int = 50) -> list:
        if not ChatRoom.query.get(room_id):
            raise ValueError("CHAT_ROOM_NOT_FOUND")
        self._assert_member(room_id, member_id)

        query = ChatMessage.query.filter_by(room_id=room_id)

        if since:
            try:
                since_dt = datetime.fromisoformat(since)
                query = query.filter(ChatMessage.created_at > since_dt)
            except ValueError:
                pass  # since 파싱 실패 시 무시하고 최신 N개 반환

        # DESC로 최신 N개 먼저 뽑은 뒤 뒤집어서 시간순으로 반환
        messages = (
            query
            .order_by(ChatMessage.created_at.desc())
            .limit(min(limit, 100))
            .all()
        )
        return [_to_message_dto(m) for m in reversed(messages)]

    def mark_read(self, room_id: str, member_id: str) -> None:
        ms = self._get_membership(room_id, member_id)
        ms.last_read_at = datetime.now(timezone.utc)
        db.session.commit()

    # ── 파일 / 이미지 첨부 ──────────────────────────────────────

    def upload_file(self, room_id: str, sender_id: str, file_storage) -> ChatMessageResponseDTO:
        """multipart/form-data의 FileStorage 객체를 받아 MinIO에 업로드 후 메시지 생성."""
        if not ChatRoom.query.get(room_id):
            raise ValueError("CHAT_ROOM_NOT_FOUND")
        self._assert_member(room_id, sender_id)

        original_name = file_storage.filename or "file"
        # 전체 읽기 전에 크기부터 확인 (초과 시 메모리에 올리지 않고 즉시 거부)
        file_storage.seek(0, 2)
        precheck_size = file_storage.tell()
        file_storage.seek(0)
        if precheck_size > MAX_FILE_SIZE:
            raise ValueError("CHAT_FILE_TOO_LARGE")
        data = file_storage.read()
        mime_type = file_storage.content_type or "application/octet-stream"
        size = len(data)
        file_id = str(uuid.uuid4())

        object_name = f"{room_id}/{file_id}/{original_name}"
        client = get_minio_client()
        try:
            client.put_object(
                bucket_name=CHAT_BUCKET,
                object_name=object_name,
                data=io.BytesIO(data),
                length=size,
                content_type=mime_type,
            )
        except S3Error as e:
            logger.error("채팅 파일 업로드 실패: %s", e)
            raise ValueError("CHAT_FILE_UPLOAD_FAILED")

        resource = StorageResource(
            resource_id=file_id,
            bucket_name=CHAT_BUCKET,
            resource_name=original_name,
            s3_key=object_name,
            owner_id=sender_id,
        )
        db.session.add(resource)

        msg_type = ChatMessageType.Image if mime_type.startswith("image/") else ChatMessageType.File
        msg = ChatMessage(
            room_id=room_id,
            sender_id=sender_id,
            message_type=msg_type,
            content=original_name,
        )
        db.session.add(msg)
        db.session.flush()

        chat_file = ChatFile(
            id=file_id,
            message_id=msg.id,
            resource_id=file_id,
            original_name=original_name,
            file_size=size,
            mime_type=mime_type,
        )
        db.session.add(chat_file)
        db.session.commit()

        dto_result = _to_message_dto(msg)
        sse.publish(
            {
                "messageId":   dto_result.message_id,
                "roomId":      dto_result.room_id,
                "senderId":    dto_result.sender_id,
                "senderName":  dto_result.sender_name,
                "messageType": dto_result.message_type,
                "content":     dto_result.content,
                "fileId":      file_id,
                "originalName": original_name,
                "mimeType":    mime_type,
                "fileSize":    size,
                "createdAt":   dto_result.created_at,
            },
            type="message",
            channel=f"room:{room_id}",
        )
        return dto_result

    def get_file_url(self, room_id: str, member_id: str, file_id: str, expires: int = 3600) -> str:
        """첨부 파일의 presigned 다운로드 URL을 반환한다."""
        self._assert_member(room_id, member_id)

        chat_file = ChatFile.query.get(file_id)
        if not chat_file or chat_file.message.room_id != room_id:
            raise ValueError("CHAT_FILE_NOT_FOUND")

        resource = StorageResource.query.get(file_id)
        if not resource or resource.is_deleted:
            raise ValueError("CHAT_FILE_NOT_FOUND")

        client = get_minio_client()
        try:
            url = client.presigned_get_object(
                bucket_name=CHAT_BUCKET,
                object_name=resource.s3_key,
                expires=timedelta(seconds=expires),
            )
        except S3Error:
            raise ValueError("CHAT_FILE_NOT_FOUND")

        return url

    # ── 내부 헬퍼 ────────────────────────────────────────────────

    def _get_membership(self, room_id: str, member_id: str) -> ChatRoomMember:
        ms = ChatRoomMember.query.filter_by(room_id=room_id, member_id=member_id, is_active=True).first()
        if not ms:
            raise ValueError("CHAT_NOT_A_MEMBER")
        return ms

    def _assert_member(self, room_id: str, member_id: str) -> None:
        self._get_membership(room_id, member_id)

    def _assert_admin(self, room_id: str, member_id: str) -> None:
        ms = self._get_membership(room_id, member_id)
        if ms.room_role != ChatRoomRole.Admin:
            raise ValueError("CHAT_PERMISSION_DENIED")

    def _publish_notice(self, room_id: str, actor_id: str, content: str) -> None:
        msg = ChatMessage(
            room_id=room_id,
            sender_id=actor_id,
            message_type=ChatMessageType.Notice,
            content=content,
        )
        db.session.add(msg)
        db.session.commit()
        sse.publish(
            {
                "messageId":   msg.id,
                "roomId":      room_id,
                "senderId":    actor_id,
                "senderName":  "",
                "messageType": "NOTICE",
                "content":     content,
                "createdAt":   msg.created_at.isoformat(),
            },
            type="message",
            channel=f"room:{room_id}",
        )
