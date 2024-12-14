from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.conf import settings
from django.db.models.signals import pre_save
from django.dispatch import receiver
import uuid
import random
import string

# Model to represent the games available on the platform
# Game Model
class Game(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    game_id = models.CharField(max_length=255, primary_key=True)  # Custom ID
    image = models.ImageField(upload_to='game_images/', null=True, blank=True)  # Optional
    slug = models.SlugField(unique=True)
    max_players = models.IntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)


    def __str__(self):
        return self.name




# Utility function to generate a unique room code
def generate_unique_room_code():
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not GameRoom.objects.filter(room_code=code).exists():
            return code

# Enum for game room statuses
class GameStatus(models.TextChoices):
    NOT_STARTED = 'Not Started'
    IN_PROGRESS = 'In Progress'
    COMPLETED = 'Completed'

# Model to represent a game room
class GameRoom(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    room_code = models.CharField(max_length=10, unique=True, blank=True, editable=False)
    is_private = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    players = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='game_rooms')
    start_time = models.DateTimeField(null=True, blank=True)
    is_started = models.CharField(
        max_length=15,
        choices=GameStatus.choices,
        default=GameStatus.NOT_STARTED
    )
    max_players = models.PositiveIntegerField(default=4)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.game.name} - {self.room_code}"

    def save(self, *args, **kwargs):
        if not self.room_code:
            self.room_code = generate_unique_room_code().upper()
        super().save(*args, **kwargs)

    def add_player(self, user):
        if self.players.count() < self.max_players:
            self.players.add(user)
        else:
            raise ValueError("Room is full.")

# Model to track player readiness in a game room
class PlayerStatus(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    game_room = models.ForeignKey(GameRoom, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    
    #is_ready = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.game_room.room_code} - {'Ready' if self.is_ready else 'Not Ready'}"

# Model to log player actions in a game room
class ActivityLog(models.Model):
    game_room = models.ForeignKey(GameRoom, on_delete=models.CASCADE)
    player = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    action = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.player.username} in {self.game_room.room_code} - {self.action}"


from django.db import models
from django.conf import settings  # Import settings to access AUTH_USER_MODEL

class Snake(models.Model):
    player = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # Correct reference to User model
    game_room = models.ForeignKey('GameRoom', on_delete=models.CASCADE)
    length = models.IntegerField(default=1)
    body_positions = models.JSONField(default=list)
    direction = models.CharField(max_length=10, default='up')
    color = models.CharField(max_length=20, default='green')
    is_alive = models.BooleanField(default=True)
    score = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.player.username}'s Snake in Room {self.game_room.id}"
