from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator

from .models import MetodoPago, TipoCobro, TipoVenta


class ProductoBase(BaseModel):
    codigo_barras: str
    nombre: str
    precio: float
    tipo_venta: TipoVenta = TipoVenta.unidad
    precio_por_kg: float | None = None
    unidades_por_paquete: int = 1
    categoria: str | None = None
    alerta_minima: float = 5


class ProductoCrear(ProductoBase):
    stock_actual: float = 0


class ProductoLeer(ProductoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    stock_actual: float


class ItemVenta(BaseModel):
    producto_id: int | None = None
    plato_id: int | None = None
    cantidad: float

    @model_validator(mode="after")
    def validar(self):
        if (self.producto_id is None) == (self.plato_id is None):
            raise ValueError("Cada ítem debe traer producto_id o plato_id, no ambos ni ninguno")
        if self.cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor que cero")
        return self


class VentaCrear(BaseModel):
    tipo: TipoCobro
    metodo_pago: MetodoPago
    vendedor_id: int
    mesa: int | None = None
    items: list[ItemVenta]


class VentaAnular(BaseModel):
    usuario_id: int
    motivo: str


class DetalleVentaLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int | None
    plato_id: int | None
    nombre: str
    cantidad: float
    precio_unitario: float
    subtotal: float


class VentaLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha_hora: datetime
    tipo: TipoCobro
    mesa: int | None
    total: float
    metodo_pago: MetodoPago
    vendedor_id: int
    anulada: bool
    motivo_anulacion: str | None
    detalles: list[DetalleVentaLeer]
