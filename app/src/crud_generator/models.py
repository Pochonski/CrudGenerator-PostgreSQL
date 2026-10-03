"""Modelos simples del área Python (esquemas, tablas, roles, extensión).

Son contenedores inmutables para que la UI futura consuma fácilmente los
resultados del catálogo. No contienen lógica SQL ni reglas de negocio.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class SchemaInfo:
    """Esquema visible para el administrador."""

    name: str


@dataclass(frozen=True)
class TableInfo:
    """Tabla real dentro de un esquema (incluye el esquema para contexto de UI)."""

    schema: str
    name: str


@dataclass(frozen=True)
class RoleInfo:
    """Rol PostgreSQL candidato para futura asignación de privilegios.

    ``can_login`` distingue usuarios (LOGIN) de roles de grupo (NOLOGIN);
    ``is_superuser`` permite a la UI advertir que otorgar EXECUTE a un
    superusuario es innecesario (ya puede hacerlo todo).
    """

    name: str
    can_login: bool
    is_superuser: bool


class ExtensionState(Enum):
    """Estados de la verificación de extensión (§4.2 del enunciado)."""

    INSTALLED = "INSTALLED"
    NOT_INSTALLED = "NOT_INSTALLED"
    NOT_ACCESSIBLE = "NOT_ACCESSIBLE"
    ERROR = "ERROR"


@dataclass(frozen=True)
class ExtensionStatus:
    """Resultado estructurado de verificar una extensión en PostgreSQL."""

    name: str
    state: ExtensionState
    version: str | None = None
    schema: str | None = None
    message: str | None = None
    sqlstate: str | None = None


class CrudOperation(Enum):
    """Operaciones CRUD seleccionables (nombres del enunciado §4.10)."""

    INSERT = "INSERT"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


@dataclass(frozen=True)
class ColumnMetadata:
    """Una columna descrita por ``crud_generator.analyze_table``.

    Refleja fielmente las 12 columnas de ``CONTRACTS.md`` §3.1, en el orden
    devuelto por la extensión (ordenadas por ``ordinal_position``).

    ``data_type`` se preserva como el texto real de ``format_type()`` (con
    precisión/escala); nunca se convierte a tipos Python. ``pk_position`` es
    ``None`` cuando la columna no es parte de la PK. ``default_expression``,
    ``identity_generation`` y ``generated_expression`` son ``None`` cuando no
    aplican (ver ``_table_columns`` en ``crud_generator--1.0.sql``).
    """

    column_name: str
    data_type: str
    ordinal_position: int
    is_primary_key: bool
    pk_position: int | None
    is_nullable: bool
    has_default: bool
    default_expression: str | None
    is_identity: bool
    identity_generation: str | None
    is_generated: bool
    generated_expression: str | None


class GenerationStatus(Enum):
    """Estados cerrados de ``generate_crud`` (``CONTRACTS.md`` §3.3)."""

    SUCCESS = "success"
    NOT_APPLICABLE = "not_applicable"
    PROCEDURE_CONFLICT = "procedure_conflict"
    VALIDATION_ERROR = "validation_error"


@dataclass(frozen=True)
class GenerationResult:
    """Una fila de ``crud_generator.generate_crud`` (una por operación).

    ``operation`` es siempre un :class:`CrudOperation`: el servicio valida
    antes de llamar a PostgreSQL que ``operations`` no esté vacío y que todos
    sus elementos sean ``CrudOperation`` (sin ``NULL``/``None`` ni strings
    arbitrarios), por lo que un ``operation = NULL`` devuelto por PostgreSQL
    a través de esta API se trata como violación de contrato (``ValueError``).

    ``identity_arguments`` se preserva como el string exacto de PostgreSQL
    (``pg_get_function_identity_arguments``); no se parsea aquí porque se
    usará tal cual para el futuro ``GRANT EXECUTE``.
    """

    operation: CrudOperation
    status: GenerationStatus
    schema_name: str
    routine_name: str | None
    identity_arguments: str | None
    message: str
    sqlstate: str | None


@dataclass(frozen=True)
class CrudSelection:
    """Selección estructurada lista para la futura generación.

    Inmutable y validada: la generación real la recibirá sin cambiar la UI.
    Todavía no incluye ningún resultado de generación.
    """

    schema: str
    tables: tuple[str, ...] = ()
    operations: tuple[CrudOperation, ...] = ()

    def __post_init__(self) -> None:
        if not self.schema.strip():
            raise ValueError("La selección requiere un esquema.")
        if not self.tables:
            raise ValueError("La selección requiere al menos una tabla.")
        if not self.operations:
            raise ValueError("La selección requiere al menos una operación.")
