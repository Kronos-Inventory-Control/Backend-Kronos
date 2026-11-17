from app.infrastructure.database.base import Base
import app.models  # noqa: F401  (registra los modelos)


def test_metadata_tiene_16_tablas():
    assert len(Base.metadata.tables) == 16


def test_metadata_tiene_18_llaves_foraneas():
    total = sum(len(t.foreign_keys) for t in Base.metadata.tables.values())
    assert total == 18