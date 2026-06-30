from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional


@dataclass
class BucketResponseDTO:
    bucket_id:   str
    bucket_name: str
    created_by:  str
    created_at:  datetime


@dataclass
class ObjectInfoDTO:
    object_name:   str
    size:          int
    etag:          str
    last_modified: datetime
    is_dir:        bool = False


@dataclass
class StatObjectDTO:
    object_name:   str
    size:          int
    etag:          str
    last_modified: datetime
    content_type:  str
    metadata:      Dict[str, str] = field(default_factory=dict)


@dataclass
class PresignedUrlDTO:
    url:        str
    expires_in: int   # seconds


@dataclass
class UploadResultDTO:
    bucket_name:  str
    object_name:  str
    etag:         str
    size:         int
