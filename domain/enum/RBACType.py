from enum import Enum


class RBACType(Enum):
    READ = "READ"
    CREATE     = "CREATE"
    DELETE = "DELETE"