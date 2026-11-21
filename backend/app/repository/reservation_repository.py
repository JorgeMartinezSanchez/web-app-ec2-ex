from ..models import Reservation
from .repository import Repository


class ReservationRepository(Repository):
    model = Reservation
