from dataclasses import dataclass, field
from typing import Optional


def _validate_member_ids(member_ids: list) -> None:
    if not isinstance(member_ids, list):
        raise ValueError("memberIds는 배열이어야 합니다.")
    if any(not isinstance(m, str) or not m.strip() for m in member_ids):
        raise ValueError("memberIds의 각 항목은 비어있지 않은 문자열이어야 합니다.")


@dataclass
class CreateGroupRequestDTO:
    group_name:  str
    description: Optional[str] = None
    member_ids:  list           = field(default_factory=list)  # [member UUID, ...]

    def __post_init__(self):
        if not self.group_name or not self.group_name.strip():
            raise ValueError("group_name은 필수입니다.")
        _validate_member_ids(self.member_ids)


@dataclass
class UpdateGroupRequestDTO:
    group_name:  Optional[str] = None
    description: Optional[str] = None

    def __post_init__(self):
        if self.group_name is not None and not self.group_name.strip():
            raise ValueError("group_name은 빈 값일 수 없습니다.")


@dataclass
class AddGroupMembersRequestDTO:
    member_ids: list    # [member UUID, ...] — 비어있으면 안 됨

    def __post_init__(self):
        if not isinstance(self.member_ids, list) or len(self.member_ids) == 0:
            raise ValueError("memberIds는 비어있지 않은 배열이어야 합니다.")
        _validate_member_ids(self.member_ids)


@dataclass
class RemoveGroupMembersRequestDTO:
    member_ids: list    # [member UUID, ...] — 비어있으면 안 됨

    def __post_init__(self):
        if not isinstance(self.member_ids, list) or len(self.member_ids) == 0:
            raise ValueError("memberIds는 비어있지 않은 배열이어야 합니다.")
        _validate_member_ids(self.member_ids)
