from enum import Enum


class VdiAction(Enum):
    CONNECT    = "CONNECT"
    DISCONNECT = "DISCONNECT"
    POWER_ON   = "POWER_ON"
    POWER_OFF  = "POWER_OFF"
    REBOOT     = "REBOOT"
    SNAPSHOT   = "SNAPSHOT"
    RESTORE    = "RESTORE"
    ASSIGN     = "ASSIGN"
    REVOKE     = "REVOKE"
    MONITOR    = "MONITOR"
    MANAGE   = "MANAGE"