from .models import User
from django.db import models

def get_leaderboard():
    return User.objects.order_by('-points').annotate(rank=models.Window(
        expression=models.F('row_number'),
        order_by=models.F('points').desc(),
    ))