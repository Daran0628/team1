import logging

from extensions import db
from domain.model.Group import Group
from domain.model.Member import Member
from web.converter.RBACConverter import RBACConverter
from web.dto.GroupRequestDTO import (
    AddGroupMembersRequestDTO,
    CreateGroupRequestDTO,
    RemoveGroupMembersRequestDTO,
    UpdateGroupRequestDTO,
)
from web.dto.GroupResponseDTO import GroupResponseDTO

logger = logging.getLogger(__name__)


class GroupService:

    def create_group(self, dto: CreateGroupRequestDTO) -> GroupResponseDTO:
        if Group.query.filter_by(group_name=dto.group_name).first():
            raise ValueError("GROUP_NAME_DUPLICATE")

        group = Group(group_name=dto.group_name, description=dto.description)

        if dto.member_ids:
            members = Member.query.filter(Member.id.in_(dto.member_ids)).all()
            if len(members) != len(dto.member_ids):
                raise ValueError("GROUP_MEMBER_NOT_FOUND")
            group.members = members

        db.session.add(group)
        db.session.commit()
        logger.info("group created: %s", group.id)
        return RBACConverter.to_group_dto(group)

    def get_all_groups(self) -> list[GroupResponseDTO]:
        return [RBACConverter.to_group_dto(g) for g in Group.query.all()]

    def get_group(self, group_id: str) -> GroupResponseDTO:
        group = Group.query.get(group_id)
        if not group:
            raise ValueError("GROUP_NOT_FOUND")
        return RBACConverter.to_group_dto(group)

    def update_group(self, group_id: str, dto: UpdateGroupRequestDTO) -> GroupResponseDTO:
        group = Group.query.get(group_id)
        if not group:
            raise ValueError("GROUP_NOT_FOUND")

        if dto.group_name is not None:
            dup = Group.query.filter_by(group_name=dto.group_name).first()
            if dup and dup.id != group_id:
                raise ValueError("GROUP_NAME_DUPLICATE")
            group.group_name = dto.group_name

        if dto.description is not None:
            group.description = dto.description

        db.session.commit()
        return RBACConverter.to_group_dto(group)

    def delete_group(self, group_id: str) -> None:
        group = Group.query.get(group_id)
        if not group:
            raise ValueError("GROUP_NOT_FOUND")
        db.session.delete(group)
        db.session.commit()
        logger.info("group deleted: %s", group_id)

    def add_members(self, group_id: str, dto: AddGroupMembersRequestDTO) -> GroupResponseDTO:
        group = Group.query.get(group_id)
        if not group:
            raise ValueError("GROUP_NOT_FOUND")

        members = Member.query.filter(Member.id.in_(dto.member_ids)).all()
        if len(members) != len(dto.member_ids):
            raise ValueError("GROUP_MEMBER_NOT_FOUND")

        existing_ids = {m.id for m in group.members}
        for m in members:
            if m.id in existing_ids:
                raise ValueError("GROUP_MEMBER_ALREADY_EXISTS")
            group.members.append(m)

        db.session.commit()
        return RBACConverter.to_group_dto(group)

    def remove_members(self, group_id: str, dto: RemoveGroupMembersRequestDTO) -> GroupResponseDTO:
        group = Group.query.get(group_id)
        if not group:
            raise ValueError("GROUP_NOT_FOUND")

        existing = {m.id: m for m in group.members}
        for mid in dto.member_ids:
            if mid not in existing:
                raise ValueError("GROUP_MEMBER_NOT_FOUND")
            group.members.remove(existing[mid])

        db.session.commit()
        return RBACConverter.to_group_dto(group)
