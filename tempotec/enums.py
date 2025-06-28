from sqlalchemy import Enum

class Status(Enum):
    PENDENTE = 0
    APROVADO = 1
    REJEITADO = 2
