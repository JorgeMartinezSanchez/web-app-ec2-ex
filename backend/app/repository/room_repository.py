from ..models import Room
from .repository import Repository


class RoomRepository(Repository):
    model = Room
