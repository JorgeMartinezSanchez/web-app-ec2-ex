### `backend/app/controllers/reservation_controller.py`

Agregué constantes para las reglas de negocio al inicio del archivo:
```python
ACTIVE_STATUSES = ("confirmed", "checked_in")
MAX_ACTIVE_RESERVATIONS = 3
LONG_STAY_NIGHTS = 7
LONG_STAY_DISCOUNT = 0.10
LATE_CANCEL_HOURS = 48
```

**Crear reserva (`POST /api/reservations`)**
1. **Habitación en mantenimiento (la 203):** si `room.status != "available"` se rechaza con 409.
2. **Fecha pasada:** si `check_in < date.today()` se rechaza con 400.
3. **Salida antes del ingreso (el total negativo):** si `check_out <= check_in` se rechaza con 400.
4. **Capacidad (la 101 para cinco personas):** `guests_count` tiene que estar entre 1 y `room.capacity`. Si no, 400.
5. **Doble venta (la 202 en carnaval):** se rechaza con 409 si la habitación ya tiene otra reserva `confirmed` o `checked_in` con fechas que se solapan:
   ```python
   Reservation.check_in < check_out and Reservation.check_out > check_in
   ```
6. **Máximo 3 reservas activas por huésped:** si ya tiene 3 reservas `confirmed` o `checked_in`, se rechaza con 409.
7. **10 % de descuento por 7 noches o más:** el total se multiplica por 0.9 y se redondea a 2 decimales.
8. Saqué el `try/except Exception` general y el `finally: db.session.close()`. Ahora cada error devuelve su propio mensaje y código.

**Cancelar (`PATCH /cancel`)**
- Solo se pueden cancelar reservas `confirmed`. Si no, 409.
- Si faltan **menos de 48 h** para el ingreso (contando desde las 00:00 del día de check-in), `total_price` pasa a ser el precio de **una noche**. Si se avisa con más tiempo, `total_price = 0`. Desde ahora, en una reserva cancelada, `total_price` es lo que realmente se cobra.

**Check-in (`PATCH /check-in`)**
- Solo se puede hacer con reservas `confirmed`, así una cancelada ya no puede pasar a hospedada. Si no, 409.
- No se puede hacer antes de la fecha de `check_in`. Si no, 409.

**Check-out (`PATCH /check-out`)**
- Solo se puede hacer con reservas `checked_in`, así nadie hace check-out sin haber hecho check-in. Si no, 409.

### `backend/app/controllers/room_controller.py`
- **Crear habitación:** `price_per_night` tiene que ser mayor a 0 y `capacity` al menos 1. Además, `status` se valida contra `ROOM_STATUSES` (antes se aceptaba cualquier texto).
- **Editar habitación (`PUT`):** las mismas validaciones de precio mayor a 0 y capacidad de al menos 1.

### Verificación
- Los 9 tests que ya había siguen pasando.
- Probé cada regla con un script aparte y todas responden con el código esperado: doble venta, fechas invertidas, fecha pasada, capacidad, mantenimiento, descuento (7 noches a 100 = 630), tope de 3 reservas, check-in adelantado, check-out sin check-in, check-in de una reserva cancelada, y cancelación con tiempo (0) y con menos de 48 h (100).

**Observación:** todavía no agregué estos casos como tests en `tests/test_api.py`. Te convendría sumarlos.