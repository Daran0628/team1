from enum import Enum


class StorageAction(Enum):
    READ     = "READ"
    DOWNLOAD = "DOWNLOAD"
    UPLOAD   = "UPLOAD"
    DELETE   = "DELETE"
    MANAGE   = "MANAGE"
