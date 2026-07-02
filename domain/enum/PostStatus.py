from enum import Enum


class PostStatus(Enum):
    Draft     = "DRAFT"
    Pending   = "PENDING"
    Published = "PUBLISHED"
    Rejected  = "REJECTED"
