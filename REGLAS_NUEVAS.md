# R1: No se puede poner una habitación en mantenimiento si este cuenta con reservas posteriores a hoy día

**room_controller.py**: en el metodo de update_room.py
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