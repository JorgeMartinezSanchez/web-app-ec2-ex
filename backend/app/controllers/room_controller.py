from datetime import date

from flask import Blueprint, jsonify, request

from ..models import Room, db
from ..views.room_view import room_to_dict, rooms_to_list

room_bp = Blueprint("rooms", __name__, url_prefix="/api/rooms")

ROOM_TYPES = ("single", "double", "family", "suite")
ROOM_STATUSES = ("available", "maintenance")


@room_bp.get("")
def list_rooms():
    query = Room.query
    status = request.args.get("status")
    if status:
        query = query.filter_by(status=status)
    rooms = query.order_by(Room.number).all()
    return jsonify(rooms_to_list(rooms))


@room_bp.get("/<int:room_id>")
def get_room(room_id):
    room = db.session.get(Room, room_id)
    if room is None:
        return jsonify({"error": "Habitación no encontrada"}), 404
    return jsonify(room_to_dict(room))


@room_bp.post("")
def create_room():
    data = request.get_json(silent=True) or {}

    missing = [f for f in ("number", "type", "price_per_night", "capacity") if data.get(f) in (None, "")]
    if missing:
        return jsonify({"error": f"Faltan campos: {', '.join(missing)}"}), 400
    if data["type"] not in ROOM_TYPES:
        return jsonify({"error": f"Tipo inválido. Usa: {', '.join(ROOM_TYPES)}"}), 400

    try:
        price = float(data["price_per_night"])
        capacity = int(data["capacity"])
    except (TypeError, ValueError):
        return jsonify({"error": "price_per_night y capacity deben ser números"}), 400
    if price <= 0 or capacity < 1:
        return jsonify({"error": "price_per_night debe ser > 0 y capacity >= 1"}), 400

    status = data.get("status", "available")
    if status not in ROOM_STATUSES:
        return jsonify({"error": f"Estado inválido. Usa: {', '.join(ROOM_STATUSES)}"}), 400

    number = str(data["number"]).strip()
    if Room.query.filter_by(number=number).first():
        return jsonify({"error": "Ya existe una habitación con ese número"}), 409

    room = Room(
        number=number,
        type=data["type"],
        price_per_night=price,
        capacity=capacity,
        status=status,
    )
    db.session.add(room)
    db.session.commit()
    return jsonify(room_to_dict(room)), 201


@room_bp.put("/<int:room_id>")
def update_room(room_id):
    room = db.session.get(Room, room_id)
    if room is None:
        return jsonify({"error": "Habitación no encontrada"}), 404

    data = request.get_json(silent=True) or {}
    if "type" in data:
        if data["type"] not in ROOM_TYPES:
            return jsonify({"error": f"Tipo inválido. Usa: {', '.join(ROOM_TYPES)}"}), 400
        room.type = data["type"]
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

    try:
        if "price_per_night" in data:
            price = float(data["price_per_night"])
            if price <= 0:
                return jsonify({"error": "price_per_night debe ser > 0"}), 400
            room.price_per_night = price
        if "capacity" in data:
            capacity = int(data["capacity"])
            if capacity < 1:
                return jsonify({"error": "capacity debe ser >= 1"}), 400
            over = [r for r in room.reservations
                    if r.status in ("confirmed", "checked_in") and r.guests_count > capacity]
            if over:
                detail = ", ".join(f"#{r.id} ({r.guests_count} huéspedes)" for r in over)
                return jsonify({"error": f"La capacidad no puede ser menor a las reservas activas: {detail}"}), 422
            room.capacity = capacity
    except (TypeError, ValueError):
        return jsonify({"error": "price_per_night y capacity deben ser números"}), 400

    db.session.commit()
    return jsonify(room_to_dict(room))


@room_bp.delete("/<int:room_id>")
def delete_room(room_id):
    room = db.session.get(Room, room_id)
    if room is None:
        return jsonify({"error": "Habitación no encontrada"}), 404
    if room.reservations:
        return jsonify({"error": "La habitación tiene reservas registradas"}), 409

    db.session.delete(room)
    db.session.commit()
    return "", 204
