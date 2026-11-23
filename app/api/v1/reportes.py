"""Historial de reportes generados desde el panel del jefe."""

import json
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.common import a_iso, exigir_staff, num, ordenar
from app.infrastructure.database.session import get_db
from app.models.reporte_generado import ReporteGenerado

router = APIRouter(prefix="/reportes", tags=["Reportes"])


def reporte_json(r: ReporteGenerado) -> dict:
    try:
        filtros = json.loads(r.filtros) if r.filtros else {}
    except ValueError:
        filtros = {}
    return {
        "id": r.idReporte,
        "tipo": r.tipo,
        "categoria": r.categoria,
        "cantidad": r.cantidad,
        "filtros": filtros,
        "valor_total": num(r.valorTotal),
        "fecha": a_iso(r.fecha),
    }


class ReporteIn(BaseModel):
    tipo: str = Field(min_length=1, max_length=80)
    categoria: str | None = Field(default=None, max_length=80)
    cantidad: int | None = None
    filtros: dict | None = None
    valor_total: float | None = None


class ReportesIn(BaseModel):
    filas: list[ReporteIn] = Field(min_length=1)


@router.get("", summary="Reportes generados")
def listar_reportes(
    orden: str | None = None, asc: bool = False,
    db: Session = Depends(get_db), _=Depends(exigir_staff),
):
    consulta = ordenar(select(ReporteGenerado), {"fecha": ReporteGenerado.fecha}, orden, asc,
                       ReporteGenerado.idReporte)
    return [reporte_json(r) for r in db.execute(consulta).scalars().all()]


@router.post("", summary="Guardar reportes generados")
def crear_reportes(body: ReportesIn, db: Session = Depends(get_db), _=Depends(exigir_staff)):
    creados = []
    for f in body.filas:
        reporte = ReporteGenerado(
            tipo=f.tipo,
            categoria=f.categoria,
            cantidad=f.cantidad,
            filtros=json.dumps(f.filtros or {}, ensure_ascii=False),
            valorTotal=Decimal(str(f.valor_total)) if f.valor_total is not None else None,
        )
        db.add(reporte)
        db.flush()
        creados.append(reporte)
    db.commit()
    for r in creados:
        db.refresh(r)
    return [reporte_json(r) for r in creados]


@router.delete("/{reporte_id}", summary="Eliminar un reporte del historial")
def eliminar_reporte(reporte_id: int, db: Session = Depends(get_db), _=Depends(exigir_staff)):
    reporte = db.get(ReporteGenerado, reporte_id)
    if reporte is None:
        raise HTTPException(status_code=404, detail="El reporte no existe.")
    fila = reporte_json(reporte)
    db.delete(reporte)
    db.commit()
    return [fila]
