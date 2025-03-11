import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import GameRoom, PlayerStatus
from django.contrib.auth.models import User
from channels.db import database_sync_to_async
from datetime import datetime




# consumer.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class ChessConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_group_name = None
        self.room_name = None
        self.players = {}  # Maps channel_name to player color
        self.game_state = {
            'board': [
                ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],
                ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],
                ['', '', '', '', '', '', '', ''],
                ['', '', '', '', '', '', '', ''],
                ['', '', '', '', '', '', '', ''],
                ['', '', '', '', '', '', '', ''],
                ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],
                ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
            ],
            'current_player': 'white',
            'move_count': 0
        }

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_code']
        self.room_group_name = f'chess_{self.room_name}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Assign player color
        if len(self.players) < 2:
            player_color = 'white' if not self.players else 'black'
            self.players[self.channel_name] = player_color
            await self.send(text_data=json.dumps({
                'type': 'player_assignment',
                'color': player_color
            }))
            await self.send_game_state()

    async def disconnect(self, close_code):
        # Leave room group
        if self.channel_name in self.players:
            del self.players[self.channel_name]
        
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # async def receive(self, text_data):
    #     data = json.loads(text_data)
    #     message_type = data.get('type')

    #     if message_type == 'join':
    #         # Already handled in connect, but we'll resend state
    #         await self.send_game_state()
        
    #     elif message_type == 'move':
    #         await self.handle_move(data)
        
    #     elif message_type == 'chat_message':
    #         await self.channel_layer.group_send(
    #             self.room_group_name,
    #             {
    #                 'type': 'chat_message',
    #                 'message': data['message']
    #             }
    #         )

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('type')

        if action == 'move':
            move = data['move']
            board = data['board']
            current_player = data['current_player']  # Client suggests the next player
            player = data['player']

            # Validate the move if needed (optional server-side check)
            next_player = 'black' if current_player == 'white' else 'white'

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chess_move_update',
                    'player': player,
                    'move': move,
                    'board': board,
                    'current_player': next_player,  # Ensure this is the next player
                }
            )

        elif action == 'chat_message':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': data['message']
                }
            )

    async def handle_move(self, data):
        player = data.get('player')
        move = data.get('move')
        board = data.get('board')
        received_current_player = data.get('currentPlayer')

        # Validate it's the correct player's turn
        if player != self.game_state['current_player']:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f"Not {player}'s turn!"
            }))
            return

        # Update game state
        self.game_state['board'] = board
        self.game_state['move_count'] += 1
        # Switch turns
        self.game_state['current_player'] = 'black' if player == 'white' else 'white'

        # Broadcast move to all players
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chess_move_update',
                'move': move,
                'board': board,
                'player': player,
                'currentPlayer': self.game_state['current_player']
            }
        )

    async def send_game_state(self):
        await self.send(text_data=json.dumps({
            'type': 'game_state',
            'board': self.game_state['board'],
            'currentPlayer': self.game_state['current_player']
        }))

    # Handler for group messages
    async def chess_move_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chess_move_update',
            'move': event['move'],
            'board': event['board'],
            'player': event['player'],
            'currentPlayer': event['currentPlayer']
        }))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message']
        }))

# class GameConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.room_code = self.scope['url_route']['kwargs']['room_code']

#         # Get the game room from the database
#         self.game_room = await self.get_game_room(self.room_code)
#         self.user = self.scope["user"]

#         # Ensure the user is part of the game room
#         if not await self.is_user_in_game(self.user, self.game_room):
#             await self.close()
#             return

#         self.room_group_name = f"game_{self.room_code}"

#         # Join room group
#         await self.channel_layer.group_add(self.room_group_name, self.channel_name)

#         # Accept the WebSocket connection
#         await self.accept()

#         # Notify all players about the new connection
#         await self.channel_layer.group_send(
#             self.room_group_name,
#             {
#                 'type': 'player_join',  # Type of message
#                 'player': self.user.username,
#             }
#         )

#     @database_sync_to_async
#     def get_game_room(self, room_code):
#         print(room_code)
#         return GameRoom.objects.get(room_code=room_code)

#     @database_sync_to_async
#     def is_user_in_game(self, user, game_room):
#         return user in game_room.players.all()

#     @database_sync_to_async
#     def get_player_status(self, user, game_room):
#         return PlayerStatus.objects.get(user=user, game_room=game_room)

#     async def disconnect(self, close_code):
#         # Leave room group when player disconnects
#         await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

#     async def receive(self, text_data):
#         data = json.loads(text_data)
#         action = data.get('type')

#         if action == 'move':
#             # Extract move details
#             move = data['move']
#             board = data['board']

#             # Broadcast updated board and move to all players
#             await self.channel_layer.group_send(
#                 self.room_group_name,
#                 {
#                     'type': 'chess_move_update',
#                     'player': self.user.username,
#                     'move': move,
#                     'board': board,  # Send the updated board
#                 }
#             )

#         elif action == 'update_score':
#             # Update score and send leaderboard update
#             player_status = await self.get_player_status(self.user, self.game_room)
#             player_status.score += int(data['score'])
#             player_status.save()

#             leaderboard = [
#                 {'username': player.user.username, 'score': player.score}
#                 for player in PlayerStatus.objects.filter(game_room=self.game_room).order_by('-score')
#             ]
#             await self.channel_layer.group_send(
#                 self.room_group_name,
#                 {
#                     'type': 'leaderboard_update',
#                     'leaderboard': leaderboard,
#                 }
#             )

#         elif data.get('type') == 'move':
#             # Handle move (broadcast to all connected players)
#             move = data['move']
#             print("consumer.py move: ",move)

#             await self.channel_layer.group_send(
#                 self.room_group_name,
#                 {
#                     'type': 'game_event',
#                     'message': f"Move {move} made by {self.user.username}"
#                 }
#             )

#         elif data.get('type') == 'chat_message':
#             # Broadcast chat message to all players in the room
#             await self.channel_layer.group_send(
#                 self.room_group_name,
#                 {
#                     'type': 'chat_message',
#                     'message': data['message']
#                 }
#             )

#     async def player_join(self, event):
#         # Handle the 'player_join' message type
#         await self.send(text_data=json.dumps({
#             'type': 'player_join',
#             'player': event['player'],
#         }))

#     async def chess_move_update(self, event):
#         # Send the updated board state to all players
#         await self.send(text_data=json.dumps({
#             'type': 'chess_move_update',
#             'player': event['player'],
#             'move': event['move'],
#             'board': event['board'],  # Ensure board is broadcasted
#         }))

#     async def leaderboard_update(self, event):
#         # Send updated leaderboard to players
#         await self.send(text_data=json.dumps({
#             'type': 'leaderboard_update',
#             'leaderboard': event['leaderboard'],
#         }))

#     async def game_event(self, event):
#         # Handle game event (e.g., move made by player)
#         message = event['message']
#         await self.send(text_data=json.dumps({
#             'type': 'game_event',
#             'message': message
#         }))

#     async def chat_message(self, event):
#         # Broadcast chat message to players
#         message = event['message']
#         await self.send(text_data=json.dumps({
#             'type': 'chat_message',
#             'message': message
#         }))

#     async def update_snakes(self, event):
#         await self.send(text_data=json.dumps({
#             'type': 'update',
#             'snakes': event['snakes'],
#             'player': event['player'],
#         }))



from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import GameRoom, PlayerStatus  # Adjust import based on your app structure
import json

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code']
        self.user = self.scope["user"]
        self.room_group_name = f"game_{self.room_code}"

        # Get the game room from the database
        self.game_room = await self.get_game_room(self.room_code)

        # Ensure the user is part of the game room
        if not await self.is_user_in_game(self.user, self.game_room):
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        # Accept the WebSocket connection
        await self.accept()

        # Assign player color
        player_color = await self.assign_player_color(self.user, self.game_room)
        if player_color == 'spectator':
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Room is full!',
            }))
            await self.close()
            return

        # Send player assignment
        await self.send(text_data=json.dumps({
            'type': 'player_assignment',
            'color': player_color,
            'player': self.user.username,
        }))

        # Notify all players about the new connection
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'player_join',
                'player': self.user.username,
            }
        )

        # Check if two players are connected to start the game
        current_players = await self.get_player_count(self.game_room)
        if current_players == 2:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'game_start',
                    'message': 'Game started with 2 players!',
                    'current_player': 'white',  # Initial turn
                }
            )

    @database_sync_to_async
    def get_game_room(self, room_code):
        return GameRoom.objects.get(room_code=room_code)

    @database_sync_to_async
    def is_user_in_game(self, user, game_room):
        return user in game_room.players.all()

    @database_sync_to_async
    def assign_player_color(self, user, game_room):
        players = list(game_room.players.all())
        if len(players) > 2:
            return 'spectator'
        if players[0] == user:
            return 'white'
        elif players[1] == user:
            return 'black'
        return 'spectator'

    @database_sync_to_async
    def get_player_count(self, game_room):
        return game_room.players.count()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # async def receive(self, text_data):
    #     data = json.loads(text_data)
    #     action = data.get('type')

    #     if action == 'move':
    #         move = data['move']
    #         board = data['board']
    #         current_player = data['current_player']  # Client suggests the next player
    #         player = data['player']

    #         # Validate the move if needed (optional server-side check)
    #         next_player = 'black' if current_player == 'white' else 'white'

    #         await self.channel_layer.group_send(
    #             self.room_group_name,
    #             {
    #                 'type': 'chess_move_update',
    #                 'player': player,
    #                 'move': move,
    #                 'board': board,
    #                 'current_player': next_player,  # Ensure this is the next player
    #             }
    #         )

    #     elif action == 'chat_message':
    #         await self.channel_layer.group_send(
    #             self.room_group_name,
    #             {
    #                 'type': 'chat_message',
    #                 'message': data['message']
    #             }
    #         )


    async def receive(self, text_data):
            data = json.loads(text_data)
            action = data.get('type')

            if action == 'move':
                move = data['move']
                board = data['board']
                player = data['player']

                # Server determines the next player based on the current player who made the move
                next_player = 'black' if player == 'white' else 'white'

                # Optional: Add server-side move validation here if desired
                # For now, trust the client’s board state

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chess_move_update',
                        'player': player,
                        'move': move,
                        'board': board,
                        'current_player': next_player,  # Server decides this
                    }
                )

            elif action == 'chat_message':
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': data['message']
                    }
                )
    async def player_join(self, event):
        await self.send(text_data=json.dumps({
            'type': 'player_join',
            'player': event['player'],
        }))

    async def game_start(self, event):
        await self.send(text_data=json.dumps({
            'type': 'game_start',
            'message': event['message'],
            'current_player': event['current_player'],
        }))

    async def chess_move_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chess_move_update',
            'player': event['player'],
            'move': event['move'],
            'board': event['board'],
            'current_player': event['current_player'],
        }))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message']
        }))

class SnakeGameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code']
        self.room_group_name = f"snake_game_{self.room_code}"

        # Initialize snake game data storage if it doesn't exist
        if not hasattr(self.channel_layer, "snake_game_data"):
            self.channel_layer.snake_game_data = {}

        # Add current player to the game room
        self.channel_layer.snake_game_data[self.channel_name] = [{"x": 100, "y": 100}]  # Default starting position

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Remove player's snake data on disconnect
        if self.channel_name in self.channel_layer.snake_game_data:
            del self.channel_layer.snake_game_data[self.channel_name]

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)

        if data.get("type") == "snake_update":
            # Update the player's snake position
            self.channel_layer.snake_game_data[self.channel_name] = data["snake"]

            # Broadcast the updated snake game state to all players
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "snake_game_update",
                    "snake_data": self.channel_layer.snake_game_data,
                }
            )

    async def snake_game_update(self, event):
        # Broadcast updated snake data to all players in the room
        await self.send(text_data=json.dumps({
            "type": "snake_game_update",
            "snake_data": event["snake_data"],
        }))
#____________




#__________Snake____
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import FootballPlayer, FootballRoom, FootballMatchScore

# Game state
game_state = {
    "players": {},  # {player_id: {"x": x, "y": y, "team": "A/B", "score": 0}}
    "ball": {"x": 400, "y": 300},
    "scores": {"teamA": 0, "teamB": 0},
}

# football_game/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

# Global game state (replace with a database or persistent store for production)
game_state = {
    "players": {},
    "scores": {"teamA": 0, "teamB": 0},
    "ball": {"x": 400, "y": 300},
}

class FootballGameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code']
        self.room_group_name = f"football_{self.room_code}"

        # Join the group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Assign player ID and team
        self.player_id = f"player_{self.channel_name}"
        self.team = "A" if len(game_state["players"]) % 2 == 0 else "B"
        game_state["players"][self.player_id] = {
            "x": 100, "y": 100,
            "team": self.team,
        }

        # Send initial state to the player
        await self.send(text_data=json.dumps({
            "type": "assign_player_id",
            "player_id": self.player_id,
            "game_state": game_state
        }))
        await self.broadcast_game_state()

    async def disconnect(self, close_code):
        # Remove player from game state
        if self.player_id in game_state["players"]:
            del game_state["players"][self.player_id]

        # Leave the group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        await self.broadcast_game_state()

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('type')

        if action == "chat_message":
            await self.handle_chat_message(data)
        elif action == "player_move":
            await self.update_player_position(data)
        elif action == "goal_scored":
            await self.update_score(data)
        elif action == "reaction":
            await self.broadcast_reaction(data)

    async def handle_chat_message(self, data):
        message = data.get("message")
        player_name = self.player_id

        # Broadcast message to group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "player_name": player_name,
                "message": message
            }
        )

    async def update_player_position(self, data):
        movement = data.get('movement', {})
        player = game_state["players"].get(self.player_id)
        if player:
            player["x"] += movement.get("x", 0) * 5
            player["y"] += movement.get("y", 0) * 5

        await self.broadcast_game_state()

    async def update_score(self, data):
        team = data.get("team")
        if team in game_state["scores"]:
            game_state["scores"][f"team{team}"] += 1
            game_state["ball"] = {"x": 400, "y": 300}

        await self.broadcast_game_state()

    async def broadcast_reaction(self, data):
        reaction = data.get("reaction")
        player_name = self.player_id

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "reaction",
                "player_name": player_name,
                "reaction": reaction
            }
        )

    async def broadcast_game_state(self):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "game_state_update",
                "game_state": game_state
            }
        )

    async def game_state_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "game_state_update",
            "game_state": event["game_state"]
        }))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "chat_message",
            "player_name": event["player_name"],
            "message": event["message"]
        }))

    async def reaction(self, event):
        await self.send(text_data=json.dumps({
            "type": "reaction",
            "player_name": event["player_name"],
            "reaction": event["reaction"]
        }))
