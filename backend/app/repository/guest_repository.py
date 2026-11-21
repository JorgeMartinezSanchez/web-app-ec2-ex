from ..models import Guest
from .repository import Repository


class GuestRepository(Repository):
    model = Guest
