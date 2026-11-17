from app.infrastructure.database.base import Base
import app.models  # noqa: F401  (registra los modelos)


def test_metadata_tiene_17_tablas():
    # 16 tablas originales + sesionesUsuario (fase de autenticación)
    assert len(Base.metadata.tables) == 17


def test_metadata_tiene_19_llaves_foraneas():
    # 18 originales + fk_sesion_usuario1
    total = sum(len(t.foreign_keys) for t in Base.metadata.tables.values())
    assert total == 19
