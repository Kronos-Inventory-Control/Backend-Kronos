"""Productos (inventarios) y categorías."""

import base64
import binascii
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.common import (
    SIN_CATEGORIA,
    exigir_staff,
    num,
    obtener_o_crear_categoria,
    obtener_o_crear_marca,
    obtener_o_crear_unidad,
    ordenar,
    siguiente_id,
)
from app.infrastructure.database.session import get_db
from app.models.categoria import Categoria
from app.models.inventario import Inventario

router = APIRouter(tags=["Catálogo"])

ORDEN_PRODUCTOS = {
    "nombre": Inventario.nombre,
    "codigo": Inventario.codigo,
    "stock_actual": Inventario.stock,
    "precio": Inventario.precioVenta,
}


def producto_json(p: Inventario, categoria: str | None) -> dict:
    return {
        "id": p.id,
        "codigo": p.codigo,
        "nombre": p.nombre,
        "categoria": categoria,
        "stock_actual": p.stock,
        "umbral_minimo": p.umbralMinimo,
        "ubicacion": p.ubicacion,
        "precio": num(p.precioVenta),
        # La UI completa esta ruta relativa con la URL del backend. No se
        # serializa el blob dentro de cada listado, lo que mantiene ágil al
        # catálogo incluso si hay muchas imágenes.
        "imagen_url": f"/productos/{p.id}/imagen" if p.imagenProducto else None,
    }


def _fila_producto(db: Session, producto_id: int) -> dict:
    fila = db.execute(
        select(Inventario, Categoria.nombreCategoria)
        .join(Categoria, Categoria.idCategoria == Inventario.categoria_idCategoria)
        .where(Inventario.id == producto_id)
    ).first()
    if fila is None:
        raise HTTPException(status_code=404, detail="El producto no existe.")
    return producto_json(*fila)


# ----------------------------------------------------------------- productos
class ProductoIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    categoria: str | None = None
    stock_actual: int = Field(default=0, ge=0)
    umbral_minimo: int = Field(default=5, ge=0)
    ubicacion: str | None = Field(default=None, max_length=100)
    precio: float | None = Field(default=None, ge=0)
    codigo: str | None = Field(default=None, max_length=45)
    imagen_base64: str | None = Field(default=None, max_length=7_000_000)


class ProductosIn(BaseModel):
    filas: list[ProductoIn] = Field(min_length=1)


class ProductoPatch(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    categoria: str | None = None
    stock_actual: int | None = Field(default=None, ge=0)
    umbral_minimo: int | None = Field(default=None, ge=0)
    ubicacion: str | None = Field(default=None, max_length=100)
    precio: float | None = Field(default=None, ge=0)
    codigo: str | None = Field(default=None, max_length=45)
    # null elimina la imagen. Se recibe como data URL o como base64 puro.
    imagen_base64: str | None = Field(default=None, max_length=7_000_000)


def _imagen_desde_base64(valor: str | None) -> bytes | None:
    """Valida la imagen enviada desde el formulario y devuelve sus bytes."""
    if valor in (None, ""):
        return None
    contenido = valor.split(",", 1)[1] if "," in valor else valor
    try:
        imagen = base64.b64decode(contenido, validate=True)
    except (ValueError, binascii.Error):
        raise HTTPException(status_code=422, detail="La imagen enviada no es válida.")
    if not imagen or len(imagen) > 5 * 1024 * 1024:
        raise HTTPException(status_code=422, detail="La imagen debe pesar como máximo 5 MB.")
    if _tipo_imagen(imagen) is None:
        raise HTTPException(status_code=422, detail="Solo se permiten imágenes JPEG, PNG, WEBP o GIF.")
    return imagen


def _tipo_imagen(imagen: bytes) -> str | None:
    if imagen.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if imagen.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if imagen.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if imagen.startswith(b"RIFF") and imagen[8:12] == b"WEBP":
        return "image/webp"
    return None


@router.get("/productos", summary="Catálogo e inventario (lectura pública)")
def listar_productos(orden: str | None = None, asc: bool = True, db: Session = Depends(get_db)):
    consulta = select(Inventario, Categoria.nombreCategoria).join(
        Categoria, Categoria.idCategoria == Inventario.categoria_idCategoria
    )
    consulta = ordenar(consulta, ORDEN_PRODUCTOS, orden, asc, Inventario.id)
    return [producto_json(p, c) for p, c in db.execute(consulta).all()]


@router.post("/productos", summary="Registrar productos")
def crear_productos(body: ProductosIn, db: Session = Depends(get_db), _=Depends(exigir_staff)):
    marca = obtener_o_crear_marca(db)
    unidad = obtener_o_crear_unidad(db)
    ids = []
    for f in body.filas:
        categoria = obtener_o_crear_categoria(db, f.categoria or SIN_CATEGORIA)
        producto = Inventario(
            id=siguiente_id(db, Inventario.id),
            codigo=f.codigo or "",
            nombre=f.nombre.strip(),
            stock=f.stock_actual,
            umbralMinimo=f.umbral_minimo,
            precioVenta=Decimal(str(f.precio or 0)),
            modelo="",
            imagenProducto=_imagen_desde_base64(f.imagen_base64),
            ubicacion=f.ubicacion,
            unidadMedida_idUnidadMedida=unidad.idUnidadVenta,
            marca_idMarca=marca.idMarca,
            categoria_idCategoria=categoria.idCategoria,
        )
        db.add(producto)
        db.flush()
        ids.append(producto.id)
    db.commit()
    return [_fila_producto(db, i) for i in ids]


@router.patch("/productos/{producto_id}", summary="Actualizar un producto")
def actualizar_producto(
    producto_id: int, body: ProductoPatch, db: Session = Depends(get_db), _=Depends(exigir_staff)
):
    producto = db.get(Inventario, producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="El producto no existe.")

    datos = body.model_dump(exclude_unset=True)
    if "nombre" in datos and datos["nombre"] is not None:
        producto.nombre = datos["nombre"].strip()
    if "codigo" in datos:
        producto.codigo = datos["codigo"] or ""
    if "stock_actual" in datos and datos["stock_actual"] is not None:
        producto.stock = datos["stock_actual"]
    if "umbral_minimo" in datos and datos["umbral_minimo"] is not None:
        producto.umbralMinimo = datos["umbral_minimo"]
    if "ubicacion" in datos:
        producto.ubicacion = datos["ubicacion"]
    if "precio" in datos and datos["precio"] is not None:
        producto.precioVenta = Decimal(str(datos["precio"]))
    if "imagen_base64" in datos:
        producto.imagenProducto = _imagen_desde_base64(datos["imagen_base64"])
    if datos.get("categoria"):
        producto.categoria_idCategoria = obtener_o_crear_categoria(db, datos["categoria"]).idCategoria

    db.commit()
    return [_fila_producto(db, producto_id)]


@router.get("/productos/{producto_id}/imagen", summary="Imagen de un producto")
def ver_imagen_producto(producto_id: int, db: Session = Depends(get_db)):
    """Sirve el blob de la imagen sin exponer la base de datos al navegador."""
    producto = db.get(Inventario, producto_id)
    if producto is None or not producto.imagenProducto:
        raise HTTPException(status_code=404, detail="El producto no tiene una imagen disponible.")
    tipo = _tipo_imagen(producto.imagenProducto)
    if tipo is None:
        raise HTTPException(status_code=415, detail="El formato de imagen almacenado no es compatible.")
    # `no-cache` permite que, después de reemplazar una foto en Stock, el
    # navegador la valide de nuevo en vez de mostrar durante una hora la
    # versión anterior con la misma URL.
    return Response(content=producto.imagenProducto, media_type=tipo, headers={"Cache-Control": "no-cache"})


@router.delete("/productos/{producto_id}", summary="Eliminar un producto")
def eliminar_producto(producto_id: int, db: Session = Depends(get_db), _=Depends(exigir_staff)):
    fila = _fila_producto(db, producto_id)
    producto = db.get(Inventario, producto_id)
    try:
        db.delete(producto)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar: el producto tiene movimientos, ventas u órdenes asociadas.",
        )
    return [fila]


# ----------------------------------------------------------------- categorías
class CategoriaIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=45)
    descripcion: str | None = Field(default=None, max_length=255)
    icono: str | None = Field(default=None, max_length=45)


class CategoriasIn(BaseModel):
    filas: list[CategoriaIn] = Field(min_length=1)


class EliminarCategoriaIn(BaseModel):
    categoria_id: int | str | None = None
    producto_ids: list = Field(default_factory=list)


def categoria_json(c: Categoria) -> dict:
    return {"id": c.idCategoria, "nombre": c.nombreCategoria, "descripcion": c.descripcion, "icono": c.icono}


@router.get("/categorias", summary="Lista de categorías (lectura pública)")
def listar_categorias(orden: str | None = None, asc: bool = True, db: Session = Depends(get_db)):
    consulta = ordenar(
        select(Categoria), {"nombre": Categoria.nombreCategoria}, orden, asc, Categoria.idCategoria
    )
    return [categoria_json(c) for c in db.execute(consulta).scalars().all()]


@router.post("/categorias", summary="Crear categorías")
def crear_categorias(body: CategoriasIn, db: Session = Depends(get_db), _=Depends(exigir_staff)):
    creadas = []
    for f in body.filas:
        nombre = " ".join(f.nombre.split())
        existente = db.execute(
            select(Categoria).where(Categoria.nombreCategoria == nombre)
        ).scalars().first()
        if existente is not None:
            raise HTTPException(status_code=409, detail=f'Ya existe una categoría llamada "{nombre}".')
        categoria = Categoria(
            idCategoria=siguiente_id(db, Categoria.idCategoria),
            nombreCategoria=nombre,
            descripcion=f.descripcion,
            icono=f.icono,
        )
        db.add(categoria)
        db.flush()
        creadas.append(categoria)
    db.commit()
    return [categoria_json(c) for c in creadas]


@router.post("/categorias/eliminar", summary="Eliminar categoría y reasignar sus productos")
def eliminar_categoria(body: EliminarCategoriaIn, db: Session = Depends(get_db), _=Depends(exigir_staff)):
    """
    En UNA transacción: los productos de la categoría pasan a «Sin categoría»
    y la categoría se borra. Si algo falla, no cambia nada.
    """
    reasignados = 0
    if body.categoria_id not in (None, ""):
        try:
            categoria_id = int(body.categoria_id)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Identificador de categoría inválido.")
        categoria = db.get(Categoria, categoria_id)
        if categoria is None:
            raise HTTPException(status_code=404, detail="La categoría no existe.")
        if categoria.nombreCategoria == SIN_CATEGORIA:
            raise HTTPException(status_code=400, detail="La categoría «Sin categoría» no se puede eliminar.")
        destino = obtener_o_crear_categoria(db, SIN_CATEGORIA)
        resultado = db.execute(
            update(Inventario)
            .where(Inventario.categoria_idCategoria == categoria_id)
            .values(categoria_idCategoria=destino.idCategoria)
        )
        reasignados = resultado.rowcount
        db.delete(categoria)
    db.commit()
    return reasignados
