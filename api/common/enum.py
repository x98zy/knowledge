from enum import StrEnum


class FileStatus(StrEnum):
    WAITING = "waiting"
    PROCESSING = "processing"
    INDEXING = "indexing"
    SUCCESS = "success"
    FAILED = "failed"


class SegmentStatus(StrEnum):
    WAITING = "waiting"
    INDEXING = "indexing"
    COMPLETED = "completed"
    ERROR = "error"


class OutBoxStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
