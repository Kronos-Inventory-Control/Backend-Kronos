from app.infrastructure.database.base import Base
import app.models  # noqa: F401  (registra los modelos)


def test_metadata_tiene_18_tablas():
    # 16 originales + sesionesUsuario (autenticación) + reportesGenerados (migración del frontend)
    assert len(Base.metadata.tables) == 18


def test_metadata_tiene_19_llaves_foraneas():
    # 18 originales + fk_sesion_usuario1
    total = sum(len(t.foreign_keys) for t in Base.metadata.tables.values())
    assert total == 19
