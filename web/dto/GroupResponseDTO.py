from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class GroupMemberDTO:
    member_id:     str
    account_id:    str
    name_ko:       str
    department_id: str


@dataclass
class GroupResponseDTO:
    group_id:    str
    group_name:  str
    description: Optional[str]
    members:     List[GroupMemberDTO] = field(default_factory=list)
