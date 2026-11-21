from flask import Blueprint, jsonify, request

from ..models import Guest, db
from ..views.guest_view import guest_to_dict, guests_to_list

guest_bp = Blueprint("guests", __name__, url_prefix="/api/guests")


@guest_bp.get("")
def list_guests():
    guests = Guest.query.order_by(Guest.full_name).all()
    return jsonify(guests_to_list(guests))


@guest_bp.get("/<int:guest_id>")
def get_guest(guest_id):
    guest = db.session.get(Guest, guest_id)
    if guest is None:
        return jsonify({"error": "Huésped no encontrado"}), 404
    return jsonify(guest_to_dict(guest))


@guest_bp.post("")
def create_guest():
    data = request.get_json(silent=True) or {}

    missing = [f for f in ("full_name", "email", "document") if not str(data.get(f, "")).strip()]
    if missing:
        return jsonify({"error": f"Faltan campos: {', '.join(missing)}"}), 400

    email = data["email"].strip().lower()
    if "@" not in email:
        return jsonify({"error": "Email inválido"}), 400
    if Guest.query.filter_by(email=email).first():
        return jsonify({"error": "Ya existe un huésped con ese email"}), 409

    document = str(data["document"]).strip()
    if Guest.query.filter_by(document=document).first():
        return jsonify({"error": "Ya existe un huésped con ese documento"}), 409

    guest = Guest(full_name=data["full_name"].strip(), email=email, document=document)
    db.session.add(guest)
    db.session.commit()
    return jsonify(guest_to_dict(guest)), 201


@guest_bp.delete("/<int:guest_id>")
def delete_guest(guest_id):
    guest = db.session.get(Guest, guest_id)
    if guest is None:
        return jsonify({"error": "Huésped no encontrado"}), 404
    if guest.reservations:
        return jsonify({"error": "El huésped tiene reservas registradas"}), 409

    db.session.delete(guest)
    db.session.commit()
    return "", 204
