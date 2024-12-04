from django.contrib import admin
from .models import Game, GameRoom, PlayerStatus, ActivityLog, GameStatus
from django.utils.html import format_html

# Custom admin for the Game model
class GameAdmin(admin.ModelAdmin):
    list_display = ('name', 'game_id', 'slug', 'max_players', 'is_active', 'created_at')
    search_fields = ('name', 'game_id', 'slug')
    list_filter = ('is_active',)
    prepopulated_fields = {'slug': ('name',)}  # Automatically generate slug from the game name
    ordering = ('-created_at',)

admin.site.register(Game, GameAdmin)

# Custom admin for the GameRoom model
class GameRoomAdmin(admin.ModelAdmin):
    list_display = ('game', 'room_code', 'created_by', 'max_players', 'is_private', 'start_time', 'is_started')
    search_fields = ('room_code', 'game__name', 'created_by__username')
    list_filter = ('is_started', 'is_private', 'game__name')
    ordering = ('-start_time',)
    actions = ['start_game', 'end_game']

    def start_game(self, request, queryset):
        queryset.update(is_started=GameStatus.IN_PROGRESS)
        self.message_user(request, "Selected game rooms have been started.")

    def end_game(self, request, queryset):
        queryset.update(is_started=GameStatus.COMPLETED)
        self.message_user(request, "Selected game rooms have been completed.")

admin.site.register(GameRoom, GameRoomAdmin)

# Custom admin for the PlayerStatus model
class PlayerStatusAdmin(admin.ModelAdmin):
    list_display = ('user', 'game_room')
    search_fields = ('user__username', 'game_room__room_code')
    #list_filter = ('is_ready',)
    ordering = ('game_room',)

admin.site.register(PlayerStatus, PlayerStatusAdmin)

# Custom admin for the ActivityLog model
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('player', 'game_room', 'action', 'timestamp')
    search_fields = ('player__username', 'game_room__room_code', 'action')
    list_filter = ('timestamp',)
    ordering = ('-timestamp',)

admin.site.register(ActivityLog, ActivityLogAdmin)
