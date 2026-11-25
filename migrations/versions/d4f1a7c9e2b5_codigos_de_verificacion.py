"""codigos de verificacion: recuperar contrasena y cambiar correo

Revision ID: d4f1a7c9e2b5
Revises: c8e2f4a6b1d3
Create Date: 2026-11-24 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd4f1a7c9e2b5'
down_revision: Union[str, Sequence[str], None] = 'c8e2f4a6b1d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('codigosVerificacion',
    sa.Column('idCodigo', sa.Integer(), autoincrement=True, nullable=False, comment='Llave primaria. Identificador autoincremental del código.'),
    sa.Column('usuario_identificacion', sa.Integer(), nullable=False, comment='Clave foránea. Usuario al que pertenece el código.'),
    sa.Column('proposito', sa.String(length=20), nullable=False, comment='Para qué se emitió: RECUPERAR_PASSWORD o CAMBIAR_CORREO.'),
    sa.Column('correoDestino', sa.String(length=120), nullable=False, comment='Correo al que se envió el código. En CAMBIAR_CORREO es el correo nuevo que se va a confirmar.'),
    sa.Column('codigoHash', sa.String(length=64), nullable=False, comment='Huella HMAC-SHA256 del código. El código en claro no se almacena.'),
    sa.Column('intentos', sa.Integer(), server_default=sa.text('0'), nullable=False, comment='Intentos fallidos de verificación. Al llegar al máximo el código se invalida.'),
    sa.Column('usado', sa.Boolean(), server_default=sa.text('0'), nullable=False, comment='1 si el código ya se usó, se reemplazó por otro o se invalidó.'),
    sa.Column('fechaCreacion', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='Fecha y hora (UTC) en que se emitió el código.'),
    sa.Column('fechaExpiracion', sa.DateTime(), nullable=False, comment='Fecha y hora (UTC) en que el código deja de ser válido.'),
    sa.ForeignKeyConstraint(['usuario_identificacion'], ['usuarios.identificacion'], name='fk_codigo_usuario1'),
    sa.PrimaryKeyConstraint('idCodigo')
    )
    op.create_index('ix_codigosVerificacion_usuario_proposito', 'codigosVerificacion', ['usuario_identificacion', 'proposito'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_codigosVerificacion_usuario_proposito', table_name='codigosVerificacion')
    op.drop_table('codigosVerificacion')
