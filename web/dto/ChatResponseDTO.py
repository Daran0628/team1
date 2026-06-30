from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class RoomMemberDTO:
    member_id:    str
    account_id:   str
    name_ko:      str
    room_role:    str
    joined_at:    str
    last_read_at: Optional[str]


@dataclass
class ChatRoomResponseDTO:
    room_id:    str
    room_type:  str
    room_name:  Optional[str]
    created_by: str
    created_at: str
    members:    List[RoomMemberDTO] = field(default_factory=list)


@dataclass
class ChatFileResponseDTO:
    file_id:       str
    original_name: str
    file_size:     int
    mime_type:     str
    created_at:    str


@dataclass
class ChatMessageResponseDTO:
    message_id:   str
    room_id:      str
    sender_id:    str
    sender_name:  str
    message_type: str
    content:      Optional[str]
    is_deleted:   bool
    created_at:   str
    files:        List[ChatFileResponseDTO] = field(default_factory=list)
