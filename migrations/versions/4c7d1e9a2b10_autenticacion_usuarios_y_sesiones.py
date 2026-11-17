"""autenticacion: campos de usuario, super admin unico y sesiones

Revision ID: 4c7d1e9a2b10
Revises: 93825522783b
Create Date: 2026-11-16 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '4c7d1e9a2b10'
down_revision: Union[str, Sequence[str], None] = '93825522783b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # --- usuarios: estado, fechas, correo único y SUPER_ADMIN único ---
    op.add_column('usuarios', sa.Column('activo', sa.Boolean(), server_default=sa.text('1'), nullable=False, comment='Indica si el usuario puede iniciar sesión (1) o está desactivado (0).'))
    op.add_column('usuarios', sa.Column('fechaCreacion', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='Fecha y hora en que se registró el usuario.'))
    op.add_column('usuarios', sa.Column('fechaActualizacion', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='Fecha y hora de la última modificación del usuario.'))
    op.add_column('usuarios', sa.Column('super_admin_slot', sa.Integer(), sa.Computed('CASE WHEN rol_idRol = 5 THEN 1 ELSE NULL END', persisted=True), nullable=True, comment='Columna generada. Vale 1 solo para el SUPER_ADMIN y, con índice único, garantiza que exista uno solo.'))
    op.create_unique_constraint('uq_usuarios_correoElectronico', 'usuarios', ['correoElectronico'])
    op.create_index('uq_usuarios_super_admin_slot', 'usuarios', ['super_admin_slot'], unique=True)

    # --- sesionesUsuario: una fila por cada JWT emitido ---
    op.create_table('sesionesUsuario',
    sa.Column('idSesion', sa.Integer(), autoincrement=True, nullable=False, comment='Llave primaria. Identificador autoincremental de la sesión.'),
    sa.Column('usuario_identificacion', sa.Integer(), nullable=False, comment='Clave foránea. Usuario dueño de la sesión.'),
    sa.Column('jti', sa.String(length=36), nullable=False, comment='Identificador único (UUID) del JWT. Permite revocar la sesión individualmente.'),
    sa.Column('ultimaActividad', sa.DateTime(), nullable=False, comment='Última actividad registrada (UTC). Se usa para el límite de inactividad.'),
    sa.Column('fechaExpiracion', sa.DateTime(), nullable=False, comment='Vencimiento absoluto de la sesión (UTC).'),
    sa.Column('activa', sa.Boolean(), server_default=sa.text('1'), nullable=False, comment='1 si la sesión sigue vigente; 0 si fue cerrada o venció.'),
    sa.Column('fechaRevocacion', sa.DateTime(), nullable=True, comment='Fecha y hora (UTC) en que se cerró o invalidó la sesión.'),
    sa.Column('direccionIp', sa.String(length=45), nullable=True, comment='Dirección IP desde la que se inició sesión.'),
    sa.Column('userAgent', sa.String(length=255), nullable=True, comment='Navegador o cliente desde el que se inició sesión.'),
    sa.Column('fechaCreacion', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='Fecha y hora en que se creó la sesión.'),
    sa.ForeignKeyConstraint(['usuario_identificacion'], ['usuarios.identificacion'], name='fk_sesion_usuario1'),
    sa.PrimaryKeyConstraint('idSesion'),
    sa.UniqueConstraint('jti')
    )
    op.create_index('ix_sesionesUsuario_usuario_identificacion', 'sesionesUsuario', ['usuario_identificacion'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_sesionesUsuario_usuario_identificacion', table_name='sesionesUsuario')
    op.drop_table('sesionesUsuario')
    op.drop_index('uq_usuarios_super_admin_slot', table_name='usuarios')
    op.drop_constraint('uq_usuarios_correoElectronico', 'usuarios', type_='unique')
    op.drop_column('usuarios', 'super_admin_slot')
    op.drop_column('usuarios', 'fechaActualizacion')
    op.drop_column('usuarios', 'fechaCreacion')
    op.drop_column('usuarios', 'activo')
