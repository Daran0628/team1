from enum import Enum


class StorageAction(Enum):
    READ     = "READ"
    DOWNLOAD = "DOWNLOAD"
    SHARE = "SHARE"
    UPLOAD   = "UPLOAD"
    DELETE   = "DELETE"
    MANAGE   = "MANAGE"
