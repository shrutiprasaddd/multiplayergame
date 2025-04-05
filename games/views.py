from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import Game, GameRoom, PlayerStatus
from django.contrib.auth.models import User
import uuid





from django.shortcuts import render
from django.http import JsonResponse
from .models import Game, GameRoom
import requests

# PlayCanvas API Details
PLAYCANVAS_API_KEY = "t9qRgISU2NQc2XmzzkvVCh6fh3maG4pP"
PLAYCANVAS_API_URL = "https://playcanvas.com/api/projects"

def fetch_playcanvas_games():
    headers = {"Authorization": f"Bearer {PLAYCANVAS_API_KEY}"}
    response = requests.get(PLAYCANVAS_API_URL, headers=headers)

    if response.status_code == 200:
        games = response.json()
        free_games = [game for game in games if game.get("isPublic", False)]  # Filtering free games
        return free_games  
    return []

def home(request):
    games = Game.objects.filter(is_active=True)
    for game in games:
        game.rooms = GameRoom.objects.filter(game=game, is_active=True).count()

    playcanvas_games = fetch_playcanvas_games()  # ✅ Now this works without an error

    return render(request, 'games/home.html', {'games': games, 'playcanvas_games': playcanvas_games})

# def home(request):
#     games = Game.objects.filter(is_active=True)
#     for game in games:
#         # Get the count of active rooms for each game
#         game.rooms = GameRoom.objects.filter(game=game, is_active=True).count()

#     return render(request, 'games/home.html', {'games': games})

# from django.views.decorators.csrf import csrf_exempt

# @csrf_exempt
# def game_room_views(request, game_id):
#     game = Game.objects.get(game_id=game_id)
    
#     if request.method == 'POST':
#         action = request.POST.get('action')
        
#         if action == 'create':
#             room_type = request.POST.get('room_type', 'public')  # Default to 'public'
            
#             # Create a new room with the selected visibility type
#             room = GameRoom.objects.create(
#                 game=game,
#                 created_by=request.user,
#                 room_code=str(uuid.uuid4())[:8].upper(),  # Ensure the room code is uppercase
#                 is_private=(room_type == 'private')
#             )
#             room.players.add(request.user)  # Add the host as a player
#             room.save()
            
#             # Return JSON response with room code
#             return JsonResponse({'room_code': room.room_code})
        
#         elif action == 'join':
#             room_code = request.POST.get('room_code', '').strip().upper()  # Normalize to uppercase
#             try:
#                 room = GameRoom.objects.get(room_code=room_code, game=game)
#                 room.players.add(request.user)  # Add user to the room
#                 room.save()
#                 return JsonResponse({'room_code': room.room_code, 'game_id': game_id})
#             except GameRoom.DoesNotExist:
#                 return JsonResponse({'error': 'Invalid room code or room does not exist'}, status=400)
    
#     return render(request, 'games/game_room.html', {'game': game})




from django.utils.timezone import now, timedelta

from django.utils.timezone import now, timedelta
from django.db.models import Count
import uuid
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from .models import Game, GameRoom

@csrf_exempt
def game_room_views(request, game_id):
    try:
        game = Game.objects.get(game_id=game_id)
    except Game.DoesNotExist:
        return render(request, 'games/game_room.html', {'game': None, 'error': 'Game not found'})

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'join_auto':
            if game.slug == "chess":
                # Find an available room with one player
                room = GameRoom.objects.filter(game=game, is_active=True, is_private=False).annotate(
                    player_count=Count('players')
                ).filter(player_count=1).first()

                if room:
                    room.players.add(request.user)
                    room.is_started = True  # Start game when both players join
                    room.save()
                else:
                    # Create a new room if no available room exists
                    room = GameRoom.objects.create(
                        game=game,
                        created_by=request.user,
                        room_code=str(uuid.uuid4())[:8].upper(),
                        is_private=False
                    )
                    room.players.add(request.user)
                    room.save()

                return JsonResponse({'room_code': room.room_code, 'game_id': game_id})

            elif game.slug == "snake":
                # Find an available room with less than 99 players
                room = GameRoom.objects.filter(game=game, is_active=True, is_private=False).annotate(
                    player_count=Count('players')
                ).filter(player_count__lt=99).first()

                if not room:
                    # Create a new room if all are full
                    room = GameRoom.objects.create(
                        game=game,
                        created_by=request.user,
                        room_code=str(uuid.uuid4())[:8].upper(),
                        is_private=False
                    )

                room.players.add(request.user)
                room.save()

                return JsonResponse({'room_code': room.room_code, 'game_id': game_id})

        elif action == 'create_private_room':
            # Create a private room
            room = GameRoom.objects.create(
                game=game,
                created_by=request.user,
                room_code=str(uuid.uuid4())[:8].upper(),
                is_private=True
            )
            room.players.add(request.user)
            room.save()
        
            

            return JsonResponse({'room_code': room.room_code, 'game_id': game_id, 'private': True})
        
        elif action == 'join':
            room_code = request.POST.get('room_code', '').strip().upper()
            try:
                room = GameRoom.objects.get(
                    room_code=room_code, 
                    game=game, 
                    is_active=True
                )
                room.players.add(request.user)
                room.save()
                return JsonResponse({
                    'room_code': room.room_code, 
                    'game_id': game_id
                })
            except GameRoom.DoesNotExist:
                return JsonResponse({
                    'error': 'Invalid room code or room does not exist'
                }, status=400)

    # Fetch all active public rooms
    public_rooms = GameRoom.objects.filter(game=game, is_active=True, is_private=False)

    return render(request, 'games/game_room.html', {
        'game': game,
        'public_rooms': public_rooms
    })



from django.urls import reverse

def game_lobby(request, room_code, game_id):
    game_room = GameRoom.objects.get(room_code=room_code)

    # Validate the game ID
    if game_room.game.game_id != game_id:
        print("Room not found")
        return redirect('home')  # Redirect to home if game ID doesn't match

    players = game_room.players.all()  # Get the players in this game room

    if request.method == 'POST':
        # Set the game room to started
        game_room.is_started = True
        game_room.save()

        # Redirect to the appropriate game start view
        return redirect(reverse('start_game', kwargs={'room_code': room_code, 'game_id': game_id}))

    return render(request, 'games/game_lobby.html', {'game_room': game_room, 'players': players})


from django.http import HttpResponseNotFound

def start_game(request, room_code, game_id):
    try:
        game_room = GameRoom.objects.get(room_code=room_code)
        game = Game.objects.get(game_id=game_id)
        
        if game_room.game.game_id != game_id:
            # Redirect to lobby if the game ID doesn't match
            return redirect('game_lobby', room_code=room_code, game_id=game_id)
        
        if game.slug == "chess":
            return render(request, 'games/chess.html', {'game_room': game_room})
        elif game.slug == "Agar.io":
            return render(request, 'games/agar.html', {'game_room': game_room})
        elif game.slug == "football":
            return render(request, 'games/football.html', {'game_room': game_room})
        elif game.slug == "snake":
            players_with_scores = []
            for player in game_room.players.all():
                # Get the player's status and score from the PlayerStatus model
                player_status = PlayerStatus.objects.filter(user=player, game_room=game_room).first()
                players_with_scores.append({
                    'username': player.username,
                    'score': player_status.score if player_status else 0,  # Default score to 0 if no status found
                })
            return render(request, 'games/snake.html', {'game_room': game_room, 'players_with_scores': players_with_scores})
        else:
            # Handle the case where the game slug doesn't match any known games
            return HttpResponseNotFound("Game not found.")
    except GameRoom.DoesNotExist:
        # Handle the case where the room does not exist
        return HttpResponseNotFound("Game room not found.")
    except Game.DoesNotExist:
        # Handle the case where the game does not exist
        return HttpResponseNotFound("Game not found.")


from django.shortcuts import render
from .models import GameRoom

def chess(request, room_code):
    try:
        # Fetch the game room by the room code
        game_room = GameRoom.objects.get(room_code=room_code)
        
        # Check if the game room is active
        if not game_room.is_active:
            return redirect('game_lobby', room_code=room_code, game_id=game_room.game.game_id)
        
        return render(request, 'games/chess.html', {'game_room': game_room})
    except GameRoom.DoesNotExist:
        # Handle the case where the room does not exist
        return HttpResponseNotFound("Game room not found.")


def snake(request, room_code):
    try:
        game_room = GameRoom.objects.get(room_code=room_code)
        if not game_room.is_active:
            return redirect('game_lobby', room_code=room_code, game_id=game_room.game.game_id)
        return render(request, 'games/snake.html', {'game_room': game_room})
    except GameRoom.DoesNotExist:
        return HttpResponseNotFound("Game room not found.")


def football(request,room_code):
    pass