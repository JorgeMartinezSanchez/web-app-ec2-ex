# Los controladores reciben la petición, aplican las reglas de negocio y devuelven la vista (JSON).
from datetime import date, datetime, time, timedelta

from flask import Blueprint, jsonify, request

from ..models import Guest, Reservation, Room, db
from ..views.reservation_view import reservation_to_dict, reservations_to_list

reservation_bp = Blueprint("reservations", __name__, url_prefix="/api/reservations")

# Variables constantes para las reglas de negocio de reservas
ACTIVE_STATUSES = ("confirmed", "checked_in")   # reservas que ocupan la habitación / cuentan como "activas"
MAX_ACTIVE_RESERVATIONS = 3                     # máximo de reservas activas por huésped
LONG_STAY_NIGHTS = 7                            # una semana completa o más...
LONG_STAY_DISCOUNT = 0.10                       # ...10 % de descuento sobre el total
LATE_CANCEL_HOURS = 48                          # cancelar con menos de 48 h cobra la primera noche


def _error(message, status):
    return jsonify({"error": message}), status


def _get_reservation_or_404(reservation_id):
    return db.session.get(Reservation, reservation_id)


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
    reservation = _get_reservation_or_404(reservation_id)
    if reservation is None:
        return _error("Reserva no encontrada", 404)
    return jsonify(reservation_to_dict(reservation))


@reservation_bp.post("")
def create_reservation():
    data = request.get_json(silent=True) or {}

    missing = [f for f in ("room_id", "guest_id", "check_in", "check_out", "guests_count") if data.get(f) in (None, "")]
    if missing:
        return _error(f"Faltan campos: {', '.join(missing)}", 400)

    try:
        room_id = int(data["room_id"])
        guest_id = int(data["guest_id"])
        check_in = date.fromisoformat(str(data["check_in"]))
        check_out = date.fromisoformat(str(data["check_out"]))
        guests_count = int(data["guests_count"])
    except (TypeError, ValueError):
        return _error("IDs y guests_count numéricos; fechas en formato AAAA-MM-DD", 400)

    room = db.session.get(Room, room_id)
    if room is None:
        return _error("Habitación no encontrada", 404)
    guest = db.session.get(Guest, guest_id)
    if guest is None:
        return _error("Huésped no encontrado", 404)

    # Habitación en refacción / mantenimiento: no se puede reservar
    if room.status != "available":
        return _error(f"La habitación {room.number} no está disponible (en mantenimiento)", 409)

    # Fechas coherentes
    if check_in < date.today():
        return _error("No se puede reservar para una fecha que ya pasó", 400)
    if check_out <= check_in:
        return _error("check_out debe ser posterior a check_in", 400)

    # Capacidad de la habitación
    if guests_count < 1 or guests_count > room.capacity:
        return _error(f"guests_count debe estar entre 1 y {room.capacity} para la habitación {room.number}", 400)

    # Sin doble venta: se solapa si (inicio existente < nueva salida) y (nueva entrada < salida existente)
    overlap = Reservation.query.filter(
        Reservation.room_id == room.id,
        Reservation.status.in_(ACTIVE_STATUSES),
        Reservation.check_in < check_out,
        Reservation.check_out > check_in,
    ).first()
    if overlap:
        return _error(
            f"La habitación {room.number} ya está reservada del {overlap.check_in.isoformat()} "
            f"al {overlap.check_out.isoformat()}", 409)

    # Máximo de reservas activas por huésped
    active_count = Reservation.query.filter(
        Reservation.guest_id == guest.id,
        Reservation.status.in_(ACTIVE_STATUSES),
    ).count()
    if active_count >= MAX_ACTIVE_RESERVATIONS:
        return _error(f"El huésped ya tiene {MAX_ACTIVE_RESERVATIONS} reservas activas", 409)

    # Total con descuento por estadía larga
    nights = (check_out - check_in).days
    total_price = nights * room.price_per_night
    if nights >= LONG_STAY_NIGHTS:
        total_price *= (1 - LONG_STAY_DISCOUNT)

    reservation = Reservation(
        room=room,
        guest=guest,
        check_in=check_in,
        check_out=check_out,
        guests_count=guests_count,
        status="confirmed",
        total_price=round(total_price, 2),
    )
    db.session.add(reservation)
    db.session.commit()
    return jsonify(reservation_to_dict(reservation)), 201


@reservation_bp.patch("/<int:reservation_id>/cancel")
def cancel_reservation(reservation_id):
    reservation = _get_reservation_or_404(reservation_id)
    if reservation is None:
        return _error("Reserva no encontrada", 404)
    if reservation.status != "confirmed":
        return _error(f"Solo se pueden cancelar reservas confirmadas (estado actual: {reservation.status})", 409)

    # Con menos de 48 h para el ingreso se cobra la primera noche; si no, no se cobra nada.
    # total_price pasa a representar lo que efectivamente se cobra.
    hours_left = (datetime.combine(reservation.check_in, time.min) - datetime.now()) / timedelta(hours=1)
    if hours_left < LATE_CANCEL_HOURS:
        reservation.total_price = reservation.room.price_per_night
    else:
        reservation.total_price = 0

    reservation.status = "cancelled"
    db.session.commit()
    return jsonify(reservation_to_dict(reservation))


@reservation_bp.patch("/<int:reservation_id>/check-in")
def check_in_reservation(reservation_id):
    reservation = _get_reservation_or_404(reservation_id)
    if reservation is None:
        return _error("Reserva no encontrada", 404)
    if reservation.status != "confirmed":
        return _error(f"Solo se puede hacer check-in de reservas confirmadas (estado actual: {reservation.status})", 409)
    if date.today() < reservation.check_in:
        return _error(f"No se puede hacer check-in antes del {reservation.check_in.isoformat()}", 409)

    reservation.status = "checked_in"
    db.session.commit()
    return jsonify(reservation_to_dict(reservation))


@reservation_bp.patch("/<int:reservation_id>/check-out")
def check_out_reservation(reservation_id):
    reservation = _get_reservation_or_404(reservation_id)
    if reservation is None:
        return _error("Reserva no encontrada", 404)
    if reservation.status != "checked_in":
        return _error(f"Solo se puede hacer check-out de huéspedes con check-in (estado actual: {reservation.status})", 409)

    reservation.status = "checked_out"
    db.session.commit()
    return jsonify(reservation_to_dict(reservation))
