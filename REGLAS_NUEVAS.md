# Nuevas reglas de negocio

### RN1: No se puede poner una habitación en mantenimiento si este cuenta con reservas posteriores a hoy día

**room_controller.py**: en el metodo de update_room
```python
    if "status" in data:
        if data["status"] not in ROOM_STATUSES:
            return jsonify({"error": f"Estado inválido. Usa: {', '.join(ROOM_STATUSES)}"}), 400

        if data["status"] == "maintenance":
            active = [r for r in room.reservations
                      if r.status in ("confirmed", "checked_in") and r.check_out > date.today()]
            if active:
                detail = ", ".join(f"#{r.id} ({r.check_in} a {r.check_out})" for r in active)
                return jsonify({"error": f"La habitación {room.number} tiene reservas activas: {detail}"}), 422
        room.status = data["status"]
```

### RN2: No reducir la capacidad de una habitacion por debajo de lo que se ha reservado

**room_controller.py**: en el metodo de update_room
```python
over = [r for r in room.reservations
        if r.status in ("confirmed", "checked_in") and r.guests_count > capacity]
if over:
    detail = ", ".join(f"#{r.id} ({r.guests_count} huéspedes)" for r in over)
    return jsonify({"error": f"La capacidad no puede ser menor a las reservas activas: {detail}"}), 422
```

### RN3: Check-in fuera de plazo (no-show)

**reservation_controller.py**: en el metodo de check_in_reservation
```python
if date.today() >= reservation.check_out:
    return _error("La reserva ya venció", 422)
```

### RN4: Documento de huésped único

**guest_controller.py**: en el metodo create_guest:
```python
document = str(data["document"]).strip()
if Guest.query.filter_by(document=document).first():
    return jsonify({"error": "Ya existe un huésped con ese documento"}), 409

guest = Guest(full_name=data["full_name"].strip(), email=email, document=document)
```

### RN5: Límites de estadía y anticipación, Al crear una reserva, se rechaza si tiene más de 30 noches o si check_in está a más de 365 días de hoy

Nuevas variables constantes:
```python
MAX_NIGHTS = 30                                 # estadía máxima por reserva
MAX_ADVANCE_DAYS = 365                          # anticipación máxima para reservar
```

**reservation_controller.py**: en create_reservation:
```python
if (check_out - check_in).days > MAX_NIGHTS:
    return _error(f"La estadía no puede superar {MAX_NIGHTS} noches", 422)
if (check_in - date.today()).days > MAX_ADVANCE_DAYS:
    return _error(f"No se puede reservar con más de {MAX_ADVANCE_DAYS} días de anticipación", 422)
```