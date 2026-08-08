from enum import StrEnum

class ResumeStatus(StrEnum):
    UPLOADED="uploaded"
    PROCESSING="processing"
    READY="ready"
    FAILED="failed"
