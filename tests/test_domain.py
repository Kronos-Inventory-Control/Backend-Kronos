"""Reglas de negocio A-E (app/domain). Python puro: no necesitan base de datos."""

from datetime import datetime
from decimal import Decimal

import pytest

from app.domain.enums.estados import EstadoGarantia, EstadoOrdenCompra, EstadoStock
from app.domain.enums.user_role import UserRole
from app.domain.exceptions import (
    CantidadInvalidaError,
    GarantiaInvalidaError,
    MaterialAgotadoError,
    MaterialDescontinuadoError,
    OrdenCompraInvalidaError,
    OrdenYaRecibidaError,
    PermisoDenegadoError,
    PrecioInvalidoError,
    StockInsuficienteError,
    TransicionInvalidaError,
    UsuarioInvalidoError,
    VentaInvalidaError,
)
from app.domain.rules import garantias, inventario, ordenes_compra, usuarios, ventas


# ------------------------------------------------------------- A. Inventario
def test_entrada_aumenta_y_salida_disminuye():
    assert inventario.aplicar_entrada(10, 5) == 15
    assert inventario.aplicar_salida(10, 4, "Martillo") == 6


def test_salida_no_puede_superar_existencias():
    with pytest.raises(StockInsuficienteError):
        inventario.aplicar_salida(3, 4, "Martillo")


def test_salida_total_deja_cero_nunca_negativo():
    assert inventario.aplicar_salida(3, 3, "Martillo") == 0


def test_cantidades_deben_ser_mayores_que_cero():
    for cantidad in (0, -1):
        with pytest.raises(CantidadInvalidaError):
            inventario.aplicar_entrada(10, cantidad)
        with pytest.raises(CantidadInvalidaError):
            inventario.aplicar_salida(10, cantidad)


def test_material_agotado_o_descontinuado_no_se_vende():
    with pytest.raises(MaterialAgotadoError):
        inventario.validar_material_vendible(0, 1, "Taladro")
    with pytest.raises(MaterialDescontinuadoError):
        inventario.validar_material_vendible(10, 1, "Taladro", descontinuado=True)
    inventario.validar_material_vendible(10, 1, "Taladro")


def test_estado_corresponde_a_la_cantidad_disponible():
    assert inventario.calcular_estado_stock(0, 5) == EstadoStock.AGOTADO
    assert inventario.calcular_estado_stock(5, 5) == EstadoStock.BAJO
    assert inventario.calcular_estado_stock(6, 5) == EstadoStock.DISPONIBLE
    assert inventario.calcular_estado_stock(50, 5, descontinuado=True) == EstadoStock.DESCONTINUADO


def test_alerta_al_alcanzar_el_minimo():
    assert inventario.requiere_alerta(5, 5) is True
    assert inventario.requiere_alerta(4, 5) is True
    assert inventario.requiere_alerta(6, 5) is False


# ----------------------------------------------------------------- B. Ventas
def test_linea_de_venta_valida():
    ventas.validar_linea_venta(2, Decimal("10.50"), stock=5, nombre="Tornillo")


def test_venta_rechaza_cantidad_precio_y_stock_invalidos():
    with pytest.raises(CantidadInvalidaError):
        ventas.validar_linea_venta(0, Decimal("1"), 5)
    with pytest.raises(PrecioInvalidoError):
        ventas.validar_linea_venta(1, Decimal("-1"), 5)
    with pytest.raises(StockInsuficienteError):
        ventas.validar_linea_venta(6, Decimal("1"), 5)


def test_venta_necesita_detalle_y_cliente():
    with pytest.raises(VentaInvalidaError):
        ventas.validar_venta(0, cliente_id=1)
    with pytest.raises(VentaInvalidaError):
        ventas.validar_venta(1, cliente_id=None)
    ventas.validar_venta(1, cliente_id=1)


# ------------------------------------------------------ C. Órdenes de compra
def test_orden_necesita_proveedor_material_y_cantidades_positivas():
    with pytest.raises(OrdenCompraInvalidaError):
        ordenes_compra.validar_orden(None, [1])
    with pytest.raises(OrdenCompraInvalidaError):
        ordenes_compra.validar_orden(1, [])
    with pytest.raises(CantidadInvalidaError):
        ordenes_compra.validar_orden(1, [3, 0])
    ordenes_compra.validar_orden(1, [3, 2])


def test_orden_sigue_el_flujo_pendiente_enviada_recibida():
    ordenes_compra.validar_transicion("pendiente", "enviada")
    ordenes_compra.validar_transicion("enviada", "recibida")
    with pytest.raises(TransicionInvalidaError):
        ordenes_compra.validar_transicion("pendiente", "recibida")
    with pytest.raises(TransicionInvalidaError):
        ordenes_compra.validar_transicion("enviada", "pendiente")
    with pytest.raises(TransicionInvalidaError):
        ordenes_compra.validar_transicion("pendiente", "confirmada")


def test_orden_recibida_no_se_recibe_ni_genera_entrada_otra_vez():
    with pytest.raises(OrdenYaRecibidaError):
        ordenes_compra.validar_transicion("recibida", "recibida")
    assert ordenes_compra.genera_entrada("enviada", "recibida") is True
    assert ordenes_compra.genera_entrada("recibida", "recibida") is False
    assert ordenes_compra.genera_entrada(EstadoOrdenCompra.PENDIENTE, "enviada") is False


# ------------------------------------------------------------- D. Garantías
def test_garantia_ligada_a_compra_y_con_fecha():
    garantias.validar_creacion("dv-12", datetime(2026, 1, 1))
    with pytest.raises(GarantiaInvalidaError):
        garantias.validar_creacion(None, datetime(2026, 1, 1))
    with pytest.raises(GarantiaInvalidaError):
        garantias.validar_creacion("dv-12", None)


def test_garantia_respeta_el_flujo_y_resuelta_no_vuelve_a_revision():
    garantias.validar_transicion("enviado", "en_revision")
    garantias.validar_transicion("en_revision", "resuelto")
    with pytest.raises(TransicionInvalidaError):
        garantias.validar_transicion("resuelto", "en_revision")
    with pytest.raises(TransicionInvalidaError):
        garantias.validar_transicion("enviado", "resuelto")
    with pytest.raises(TransicionInvalidaError):
        garantias.validar_transicion("enviado", "aprobada")
    assert garantias.normalizar_estado("resuelto") == EstadoGarantia.RESUELTO


def test_garantia_conserva_observaciones():
    garantias.validar_observaciones_conservadas(["a"], ["a", "b"])
    garantias.validar_observaciones_conservadas(["a"], None)
    with pytest.raises(GarantiaInvalidaError):
        garantias.validar_observaciones_conservadas(["a", "b"], ["b"])


# ------------------------------------------------------- E. Usuarios y roles
def test_rol_debe_ser_valido():
    assert usuarios.validar_rol(3) == UserRole.JEFE
    with pytest.raises(UsuarioInvalidoError):
        usuarios.validar_rol(99)


def test_roles_determinan_las_operaciones():
    assert usuarios.puede_ejecutar(UserRole.SUPER_ADMIN, usuarios.Operacion.GESTIONAR_USUARIOS)
    for rol in (UserRole.CLIENTE, UserRole.PROVEEDOR, UserRole.EMPLEADO, UserRole.JEFE):
        assert not usuarios.puede_ejecutar(rol, usuarios.Operacion.GESTIONAR_USUARIOS)
    assert usuarios.puede_ejecutar(UserRole.JEFE, usuarios.Operacion.REGISTRAR_MOVIMIENTOS)
    assert not usuarios.puede_ejecutar(UserRole.CLIENTE, usuarios.Operacion.REGISTRAR_MOVIMIENTOS)


def test_cliente_no_ejecuta_operaciones_de_administracion():
    with pytest.raises(PermisoDenegadoError):
        usuarios.exigir_permiso(UserRole.CLIENTE, usuarios.Operacion.GESTIONAR_USUARIOS)


def test_proveedor_solo_gestiona_sus_ordenes():
    assert usuarios.proveedor_gestiona_orden(4, 4) is True
    assert usuarios.proveedor_gestiona_orden(4, 5) is False
    assert usuarios.proveedor_gestiona_orden(None, 5) is False


def test_perfiles_coherentes_con_el_rol():
    usuarios.validar_perfiles_para_rol(UserRole.CLIENTE, False, False)
    usuarios.validar_perfiles_para_rol(UserRole.PROVEEDOR, False, True)
    usuarios.validar_perfiles_para_rol(UserRole.JEFE, False, False)
    with pytest.raises(UsuarioInvalidoError):
        usuarios.validar_perfiles_para_rol(UserRole.SUPER_ADMIN, False, False)
    with pytest.raises(UsuarioInvalidoError):
        usuarios.validar_perfiles_para_rol(UserRole.PROVEEDOR, False, False)
    with pytest.raises(UsuarioInvalidoError):
        usuarios.validar_perfiles_para_rol(UserRole.CLIENTE, False, True)
    with pytest.raises(UsuarioInvalidoError):
        usuarios.validar_perfiles_para_rol(UserRole.EMPLEADO, True, False)


def test_no_se_toca_al_super_admin_ni_se_autodesactiva():
    with pytest.raises(UsuarioInvalidoError):
        usuarios.validar_edicion(UserRole.SUPER_ADMIN)
    with pytest.raises(UsuarioInvalidoError):
        usuarios.validar_cambio_estado(UserRole.SUPER_ADMIN, 1, 2, activar=False)
    with pytest.raises(UsuarioInvalidoError):
        usuarios.validar_cambio_estado(UserRole.JEFE, 7, 7, activar=False)
    usuarios.validar_cambio_estado(UserRole.JEFE, 7, 1, activar=False)
    usuarios.validar_cambio_estado(UserRole.JEFE, 7, 7, activar=True)


def test_identificacion_valida():
    usuarios.validar_identificacion(1001)
    with pytest.raises(UsuarioInvalidoError):
        usuarios.validar_identificacion(0)
