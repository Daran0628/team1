from enum import Enum


class BoardAction(Enum):
    CREATE  = "CREATE"
    UPDATE  = "UPDATE"
    DELETE  = "DELETE"
    READ    = "READ"
    APPROVE = "APPROVE"
    MANAGE  = "MANAGE"
