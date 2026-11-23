"""migracion del frontend: campos que usan las pantallas y tabla de reportes

Revision ID: c8e2f4a6b1d3
Revises: 4c7d1e9a2b10
Create Date: 2026-11-17 12:00:00.000000

Qué hace:
- Agrega a categorias, inventarios, movimientos, ordenesCompra, detalleVentas,
  proveedores y garantias las columnas que antes vivían en Supabase.
- Permite movimientos y garantías sin detalle de venta (entradas y salidas
  manuales; garantías contra proveedor).
- Crea la tabla reportesGenerados.
- Inserta los roles 1 a 4 si todavía no existen.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = 'c8e2f4a6b1d3'
down_revision: Union[str, Sequence[str], None] = '4c7d1e9a2b10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- categorias ---
    op.add_column('categorias', sa.Column('descripcion', sa.String(255), nullable=True))
    op.add_column('categorias', sa.Column('icono', sa.String(45), nullable=True))

    # --- inventarios ---
    op.add_column('inventarios', sa.Column('ubicacion', sa.String(100), nullable=True))
    op.alter_column('inventarios', 'imagenProducto', existing_type=mysql.MEDIUMBLOB(), nullable=True)
    op.alter_column('inventarios', 'nombre', existing_type=sa.String(45),
                    type_=sa.String(120), existing_nullable=False)

    # --- movimientos ---
    op.add_column('movimientos', sa.Column('motivo', sa.String(255), nullable=True))
    op.add_column('movimientos', sa.Column('responsable', sa.String(120), nullable=True))
    op.alter_column('movimientos', 'detalleVenta_idDetalleVenta',
                    existing_type=sa.Integer(), nullable=True)

    # --- ordenesCompra ---
    op.add_column('ordenesCompra', sa.Column('observacion', sa.String(255), nullable=True))

    # --- detalleVentas (pedidos de clientes) ---
    op.add_column('detalleVentas', sa.Column('codigo', sa.String(45), nullable=True))
    op.add_column('detalleVentas', sa.Column(
        'estado', sa.String(20), nullable=False, server_default='pendiente'))
    op.add_column('detalleVentas', sa.Column('observacion', sa.String(255), nullable=True))

    # --- proveedores ---
    op.add_column('proveedores', sa.Column('nit', sa.String(30), nullable=True))

    # --- usuarios: correos más largos ---
    op.alter_column('usuarios', 'correoElectronico', existing_type=sa.String(45),
                    type_=sa.String(120), existing_nullable=False)

    # --- garantias ---
    op.alter_column('garantias', 'observacion', existing_type=sa.String(45),
                    type_=sa.Text(), existing_nullable=False)
    op.alter_column('garantias', 'motivo', existing_type=sa.String(45),
                    type_=sa.Text(), existing_nullable=False)
    op.alter_column('garantias', 'evidenciaImg', existing_type=mysql.MEDIUMBLOB(), nullable=True)
    op.alter_column('garantias', 'detalleventa_idDetalleVenta',
                    existing_type=sa.Integer(), nullable=True)
    op.add_column('garantias', sa.Column('ordenRef', sa.String(20), nullable=True))
    op.add_column('garantias', sa.Column('numeroOrden', sa.String(60), nullable=True))
    op.add_column('garantias', sa.Column('clienteId', sa.Integer(), nullable=True))
    op.add_column('garantias', sa.Column('clienteNombre', sa.String(120), nullable=True))
    op.add_column('garantias', sa.Column('correo', sa.String(120), nullable=True))
    op.add_column('garantias', sa.Column('producto', sa.String(120), nullable=True))
    op.add_column('garantias', sa.Column('imagenNombre', sa.String(255), nullable=True))
    op.add_column('garantias', sa.Column('observaciones', sa.Text(), nullable=True))
    op.add_column('garantias', sa.Column('bitacora', sa.Text(), nullable=True))

    # --- reportesGenerados ---
    op.create_table(
        'reportesGenerados',
        sa.Column('idReporte', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tipo', sa.String(80), nullable=False),
        sa.Column('categoria', sa.String(80), nullable=True),
        sa.Column('cantidad', sa.Integer(), nullable=True),
        sa.Column('filtros', sa.Text(), nullable=True),
        sa.Column('valorTotal', sa.Numeric(14, 2), nullable=True),
        sa.Column('fecha', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('idReporte'),
    )

    # --- roles base (no pisa los que ya existan) ---
    for id_rol, nombre in ((1, 'CLIENTE'), (2, 'PROVEEDOR'), (3, 'JEFE'), (4, 'EMPLEADO')):
        op.execute(
            sa.text("INSERT IGNORE INTO roles (idRol, nombreRol) VALUES (:i, :n)")
            .bindparams(i=id_rol, n=nombre)
        )


def downgrade() -> None:
    op.drop_table('reportesGenerados')

    for col in ('bitacora', 'observaciones', 'imagenNombre', 'producto', 'correo',
                'clienteNombre', 'clienteId', 'numeroOrden', 'ordenRef'):
        op.drop_column('garantias', col)
    op.alter_column('garantias', 'detalleventa_idDetalleVenta',
                    existing_type=sa.Integer(), nullable=False)
    op.alter_column('garantias', 'evidenciaImg', existing_type=mysql.MEDIUMBLOB(), nullable=False)
    op.alter_column('garantias', 'motivo', existing_type=sa.Text(),
                    type_=sa.String(45), existing_nullable=False)
    op.alter_column('garantias', 'observacion', existing_type=sa.Text(),
                    type_=sa.String(45), existing_nullable=False)

    op.alter_column('usuarios', 'correoElectronico', existing_type=sa.String(120),
                    type_=sa.String(45), existing_nullable=False)

    op.drop_column('proveedores', 'nit')
    op.drop_column('detalleVentas', 'observacion')
    op.drop_column('detalleVentas', 'estado')
    op.drop_column('detalleVentas', 'codigo')
    op.drop_column('ordenesCompra', 'observacion')

    op.alter_column('movimientos', 'detalleVenta_idDetalleVenta',
                    existing_type=sa.Integer(), nullable=False)
    op.drop_column('movimientos', 'responsable')
    op.drop_column('movimientos', 'motivo')

    op.alter_column('inventarios', 'nombre', existing_type=sa.String(120),
                    type_=sa.String(45), existing_nullable=False)
    op.alter_column('inventarios', 'imagenProducto', existing_type=mysql.MEDIUMBLOB(), nullable=False)
    op.drop_column('inventarios', 'ubicacion')

    op.drop_column('categorias', 'icono')
    op.drop_column('categorias', 'descripcion')
