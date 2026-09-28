from dataclasses import dataclass, field


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    database: str
    user: str
    password: str = field(repr=False)

    def __post_init__(self) -> None:
        if not self.host.strip():
            raise ValueError("El servidor no puede estar vacío.")

        if not 1 <= self.port <= 65535:
            raise ValueError("El puerto debe estar entre 1 y 65535.")

        if not self.database.strip():
            raise ValueError("El nombre de la base de datos no puede estar vacío.")

        if not self.user.strip():
            raise ValueError("El usuario no puede estar vacío.")