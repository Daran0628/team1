from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CreateRoomRequestDTO:
    room_type: str
    member_ids: list = field(default_factory=list)
    room_name: Optional[str] = None

    def __post_init__(self):
        if self.room_type not in ("DIRECT", "GROUP"):
            raise ValueError("roomType은 DIRECT 또는 GROUP이어야 합니다.")
        if self.room_type == "GROUP" and not (self.room_name and self.room_name.strip()):
            raise ValueError("GROUP 채팅방은 roomName이 필수입니다.")
        if self.room_type == "DIRECT" and len(self.member_ids) != 1:
            raise ValueError("DIRECT 채팅방은 memberIds에 상대방 1명만 지정해야 합니다.")
        if self.room_type == "GROUP" and len(self.member_ids) == 0:
            raise ValueError("GROUP 채팅방은 memberIds가 비어있으면 안 됩니다.")


@dataclass
class SendMessageRequestDTO:
    message_type: str
    content: Optional[str] = None

    def __post_init__(self):
        if self.message_type not in ("TEXT", "FILE", "IMAGE", "NOTICE"):
            raise ValueError("messageType은 TEXT, FILE, IMAGE, NOTICE 중 하나여야 합니다.")
        if self.message_type == "TEXT" and not (self.content and self.content.strip()):
            raise ValueError("TEXT 메시지는 content가 필수입니다.")


@dataclass
class AddRoomMembersRequestDTO:
    member_ids: list

    def __post_init__(self):
        if not isinstance(self.member_ids, list) or len(self.member_ids) == 0:
            raise ValueError("memberIds는 비어있지 않은 배열이어야 합니다.")


@dataclass
class LeaveRoomRequestDTO:
    new_admin_id: Optional[str] = None
