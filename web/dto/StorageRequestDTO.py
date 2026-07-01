from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class CreateBucketRequestDTO:
    bucket_name: str

    def __post_init__(self):
        if not self.bucket_name or not self.bucket_name.strip():
            raise ValueError("bucket_name은 필수입니다.")
        if len(self.bucket_name) < 3 or len(self.bucket_name) > 63:
            raise ValueError("bucket_name은 3~63자여야 합니다.")


@dataclass
class CopyObjectRequestDTO:
    source_object: str
    dest_bucket:   str
    dest_object:   str

    def __post_init__(self):
        if not all([self.source_object, self.dest_bucket, self.dest_object]):
            raise ValueError("sourceObject, destBucket, destObject는 필수입니다.")


@dataclass
class SetObjectTagsRequestDTO:
    object_name: str
    tags:        Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self.object_name:
            raise ValueError("objectName은 필수입니다.")
        if not isinstance(self.tags, dict):
            raise ValueError("tags는 object여야 합니다.")
