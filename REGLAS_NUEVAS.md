# RN1: No se puede poner una habitación en mantenimiento si este cuenta con reservas posteriores a hoy día

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
                return jsonify({"error": f"La habitación {room.number} tiene reservas activas: {detail}"}), 409
        room.status = data["status"]
```

# RN2: No reducir la capacidad de una habitacion por debajo de lo que se ha reservado

**room_controller.py**: en el metodo de update_room
```python
over = [r for r in room.reservations
        if r.status in ("confirmed", "checked_in") and r.guests_count > capacity]
if over:
    detail = ", ".join(f"#{r.id} ({r.guests_count} huéspedes)" for r in over)
    return jsonify({"error": f"La capacidad no puede ser menor a las reservas activas: {detail}"}), 409
```

# RN3: Check-in fuera de plazo (no-show)

**reservation_controller.py**: en el metodo de check_in_reservation
```python
if date.today() >= reservation.check_out:
    return _error("La reserva ya venció", 409)
```