from datetime import date

from flask import Blueprint, jsonify, request

from ..models import Guest, Reservation, Room, db
from ..views.reservation_view import reservation_to_dict, reservations_to_list

reservation_bp = Blueprint("reservations", __name__, url_prefix="/api/reservations")


@reservation_bp.get("")
def list_reservations():
    query = Reservation.query
    status = request.args.get("status")
    guest_id = request.args.get("guest_id", type=int)
    if status:
        query = query.filter_by(status=status)
    if guest_id:
        query = query.filter_by(guest_id=guest_id)
    reservations = query.order_by(Reservation.check_in).all()
    return jsonify(reservations_to_list(reservations))


@reservation_bp.get("/<int:reservation_id>")
def get_reservation(reservation_id):
    reservation = db.session.get(Reservation, reservation_id)
    if reservation is None:
        return jsonify({"error": "Reserva no encontrada"}), 404
    return jsonify(reservation_to_dict(reservation))


@reservation_bp.post("")
def create_reservation():
    data = request.get_json(silent=True) or {}
    try:
        missing = [f for f in ("room_id", "guest_id", "check_in", "check_out", "guests_count") if data.get(f) in (None, "")]
        if missing:
            return jsonify({"error": f"Faltan campos: {', '.join(missing)}"}), 400

        room = db.session.get(Room, int(data["room_id"]))
        if room is None:
            return jsonify({"error": "Habitación no encontrada"}), 404
        guest = db.session.get(Guest, int(data["guest_id"]))
        if guest is None:
            return jsonify({"error": "Huésped no encontrado"}), 404

        try:
            check_in = date.fromisoformat(data["check_in"])
            check_out = date.fromisoformat(data["check_out"])
            guests_count = int(data["guests_count"])
        except (TypeError, ValueError):
            return jsonify({"error": "Fechas en formato AAAA-MM-DD y guests_count numérico"}), 400

        if check_in >= check_out:
            return jsonify({"error": "check_in debe ser antes de check_out"}), 400

        if guests_count < 1 or guests_count > room.capacity:
            return jsonify({"error": f"guests_count debe estar entre 1 y {room.capacity}"}), 400

        nights = (check_out - check_in).days
        total_price = nights * room.price_per_night

        reservation = Reservation(
            room=room,
            guest=guest,
            check_in=check_in,
            check_out=check_out,
            guests_count=guests_count,
            status="confirmed",
            total_price=total_price,
        )
        db.session.add(reservation)
        db.session.commit()
        return jsonify(reservation_to_dict(reservation)), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        db.session.close()

@reservation_bp.patch("/<int:reservation_id>/cancel")
def cancel_reservation(reservation_id):
    reservation = db.session.get(Reservation, reservation_id)
    if reservation is None:
        return jsonify({"error": "Reserva no encontrada"}), 404

    reservation.status = "cancelled"
    db.session.commit()
    return jsonify(reservation_to_dict(reservation))


@reservation_bp.patch("/<int:reservation_id>/check-in")
def check_in_reservation(reservation_id):
    reservation = db.session.get(Reservation, reservation_id)
    if reservation is None:
        return jsonify({"error": "Reserva no encontrada"}), 404

    reservation.status = "checked_in"
    db.session.commit()
    return jsonify(reservation_to_dict(reservation))


@reservation_bp.patch("/<int:reservation_id>/check-out")
def check_out_reservation(reservation_id):
    reservation = db.session.get(Reservation, reservation_id)
    if reservation is None:
        return jsonify({"error": "Reserva no encontrada"}), 404

    reservation.status = "checked_out"
    db.session.commit()
    return jsonify(reservation_to_dict(reservation))
