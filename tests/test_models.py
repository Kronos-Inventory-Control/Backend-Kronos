from app.infrastructure.database.base import Base
import app.models  # noqa: F401  (registra los modelos)


def test_metadata_tiene_19_tablas():
    # 16 originales + sesionesUsuario (autenticación) + reportesGenerados (migración del frontend)
    # + codigosVerificacion (recuperar contraseña / cambiar correo)
    assert len(Base.metadata.tables) == 19


def test_metadata_tiene_20_llaves_foraneas():
    # 19 anteriores + fk_codigo_usuario1
    total = sum(len(t.foreign_keys) for t in Base.metadata.tables.values())
    assert total == 20
