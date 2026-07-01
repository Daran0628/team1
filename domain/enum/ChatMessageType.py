from enum import Enum

class ChatMessageType(Enum):
    Text   = "TEXT"
    File   = "FILE"
    Image  = "IMAGE"
    Notice = "NOTICE"
