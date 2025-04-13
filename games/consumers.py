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

# class SnakeGameConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.room_code = self.scope['url_route']['kwargs']['room_code']
#         self.room_group_name = f"snake_game_{self.room_code}"

#         # Initialize snake game data storage if it doesn't exist
#         if not hasattr(self.channel_layer, "snake_game_data"):
#             self.channel_layer.snake_game_data = {}

#         # Add current player to the game room
#         self.channel_layer.snake_game_data[self.channel_name] = [{"x": 100, "y": 100}]  # Default starting position

#         await self.channel_layer.group_add(self.room_group_name, self.channel_name)
#         await self.accept()

#     async def disconnect(self, close_code):
#         # Remove player's snake data on disconnect
#         if self.channel_name in self.channel_layer.snake_game_data:
#             del self.channel_layer.snake_game_data[self.channel_name]

#         await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

#     async def receive(self, text_data):
#         data = json.loads(text_data)

#         if data.get("type") == "snake_update":
#             # Update the player's snake position
#             self.channel_layer.snake_game_data[self.channel_name] = data["snake"]

#             # Broadcast the updated snake game state to all players
#             await self.channel_layer.group_send(
#                 self.room_group_name,
#                 {
#                     "type": "snake_game_update",
#                     "snake_data": self.channel_layer.snake_game_data,
#                 }
#             )

#     async def snake_game_update(self, event):
#         # Broadcast updated snake data to all players in the room
#         await self.send(text_data=json.dumps({
#             "type": "snake_game_update",
#             "snake_data": event["snake_data"],
#         }))




import json
import random
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class SnakeGameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code']
        self.room_group_name = f"snake_game_{self.room_code}"

        # Initialize game data storage per room
        if not hasattr(self.channel_layer, "game_data"):
            self.channel_layer.game_data = {}
        if self.room_group_name not in self.channel_layer.game_data:
            self.channel_layer.game_data[self.room_group_name] = {
                "snake_data": {},
                "food_data": {}
            }

        # Add player with initial snake and score
        self.channel_layer.game_data[self.room_group_name]["snake_data"][self.channel_name] = {
            "snake": [{"x": 100, "y": 100}],
            "score": 0
        }

        # Spawn initial food
        await self.spawn_food()

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if self.room_group_name in self.channel_layer.game_data:
            if self.channel_name in self.channel_layer.game_data[self.room_group_name]["snake_data"]:
                # Convert disconnected snake to food
                snake = self.channel_layer.game_data[self.room_group_name]["snake_data"][self.channel_name]["snake"]
                for segment in snake:
                    food_id = f"{self.channel_name}_{random.randint(0, 1000000)}"
                    self.channel_layer.game_data[self.room_group_name]["food_data"][food_id] = {
                        "x": segment["x"],
                        "y": segment["y"],
                        "pulse": 1,
                        "grow": True,
                        "color": "orange",
                        "points": 15,
                        "baseSize": 8
                    }
                del self.channel_layer.game_data[self.room_group_name]["snake_data"][self.channel_name]
            # Clean up empty rooms
            if not self.channel_layer.game_data[self.room_group_name]["snake_data"]:
                del self.channel_layer.game_data[self.room_group_name]
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        game_data = self.channel_layer.game_data[self.room_group_name]

        if data.get("type") == "snake_update":
            # Update player's snake and score
            game_data["snake_data"][self.channel_name] = {
                "snake": data["snake"],
                "score": data["score"]
            }

            # Check for collisions
            collided_channels = []
            for channel, player_data in game_data["snake_data"].items():
                head = player_data["snake"][0]
                for other_channel, other_player_data in game_data["snake_data"].items():
                    if channel != other_channel:
                        for segment in other_player_data["snake"]:
                            if abs(head["x"] - segment["x"]) < 20 and abs(head["y"] - segment["y"]) < 20:
                                collided_channels.append(channel)
                                break
                if channel in collided_channels:
                    break

            # Handle collisions
            for channel in set(collided_channels):
                snake = game_data["snake_data"][channel]["snake"]
                for segment in snake:
                    food_id = f"{channel}_{len(game_data['food_data'])}"
                    game_data["food_data"][food_id] = {
                        "x": segment["x"],
                        "y": segment["y"],
                        "pulse": 1,
                        "grow": True,
                        "color": "orange",
                        "points": 15,
                        "baseSize": 8
                    }
                game_data["snake_data"][channel] = {
                    "snake": [{"x": random.randint(-1000, 1000), "y": random.randint(-1000, 1000)}],
                    "score": 0
                }

            # Broadcast game state
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "snake_game_update",
                    "snake_data": game_data["snake_data"],
                    "food_data": game_data["food_data"]
                }
            )

        elif data.get("type") == "food_eaten":
            # Remove eaten food
            food_keys = list(game_data["food_data"].keys())
            for index in sorted(data.get("eaten_indices", []), reverse=True):
                if index < len(food_keys):
                    del game_data["food_data"][food_keys[index]]
            # Update player's score
            game_data["snake_data"][self.channel_name]["score"] = data["score"]
            # Spawn new food
            await self.spawn_food(snake_head=data.get("snake_head"))
            # Broadcast updated state
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "snake_game_update",
                    "snake_data": game_data["snake_data"],
                    "food_data": game_data["food_data"]
                }
            )

        elif data.get("type") == "request_food":
            await self.spawn_food(snake_head=data.get("snake_head"))
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "snake_game_update",
                    "snake_data": game_data["snake_data"],
                    "food_data": game_data["food_data"]
                }
            )

        elif data.get("type") == "request_initial_state":
            await self.send(text_data=json.dumps({
                "type": "snake_game_update",
                "snake_data": game_data["snake_data"],
                "food_data": game_data["food_data"]
            }))

    async def spawn_food(self, snake_head=None):
        game_data = self.channel_layer.game_data[self.room_group_name]
        types = [
            {"color": "red", "points": 30, "size": 8},
            {"color": "yellow", "points": 20, "size": 10},
            {"color": "blue", "points": 10, "size": 14},
        ]
        # Ensure at least 5 foods, up to 10
        while len(game_data["food_data"]) < 10:
            type_data = random.choice(types)
            food_id = f"food_{random.randint(0, 1000000)}"
            if snake_head:
                # Spawn food within 500 units of snake head
                x = snake_head["x"] + random.randint(-500, 500)
                y = snake_head["y"] + random.randint(-500, 500)
            else:
                x = random.randint(-1000, 1000)
                y = random.randint(-1000, 1000)
            game_data["food_data"][food_id] = {
                "x": x,
                "y": y,
                "pulse": 1,
                "grow": True,
                "color": type_data["color"],
                "points": type_data["points"],
                "baseSize": type_data["size"]
            }
        # Remove excess food if more than 10
        while len(game_data["food_data"]) > 10:
            food_keys = list(game_data["food_data"].keys())
            del game_data["food_data"][food_keys[0]]

    async def snake_game_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "snake_game_update",
            "snake_data": event["snake_data"],
            "food_data": event["food_data"]
        }))
#____________snake end_________




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



import json
from channels.generic.websocket import AsyncWebsocketConsumer

class FootballGameConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.game_state = {
            'players': {
                'A_gk': {'x': 50, 'y': 300, 'team': 'A', 'role': 'goalkeeper'},
                'A_1': {'x': 200, 'y': 150, 'team': 'A', 'role': 'field'},
                'A_2': {'x': 200, 'y': 300, 'team': 'A', 'role': 'field'},
                'A_3': {'x': 200, 'y': 450, 'team': 'A', 'role': 'field'},
                'A_4': {'x': 350, 'y': 300, 'team': 'A', 'role': 'field'},
                'B_gk': {'x': 950, 'y': 300, 'team': 'B', 'role': 'goalkeeper'},
                'B_1': {'x': 800, 'y': 150, 'team': 'B', 'role': 'field'},
                'B_2': {'x': 800, 'y': 300, 'team': 'B', 'role': 'field'},
                'B_3': {'x': 800, 'y': 450, 'team': 'B', 'role': 'field'},
                'B_4': {'x': 650, 'y': 300, 'team': 'B', 'role': 'field'}
            },
            'ball': {'x': 500, 'y': 300, 'vx': 0, 'vy': 0},
            'scores': {'A': 0, 'B': 0}
        }
        self.connected_players = {}

    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code']
        self.room_group_name = f'football_{self.room_code}'
        
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        
        # Assign player on connect
        team = 'A' if len([p for p in self.connected_players.values() if p['team'] == 'A']) < 5 else 'B'
        available_players = [p for p in self.game_state['players'].keys() 
                            if p.startswith(team) and p not in [cp['player_id'] for cp in self.connected_players.values()]]
        player_id = available_players[0] if available_players else "A_1"  # Default to A_1 if none available
        
        self.connected_players[self.channel_name] = {'player_id': player_id, 'team': team}
        await self.send(json.dumps({
            'type': 'assign_player',
            'player_id': player_id,
            'team': team,
            'game_state': self.game_state
        }))
        print(f"Assigned {player_id} to {team}")

    async def disconnect(self, close_code):
        if self.channel_name in self.connected_players:
            del self.connected_players[self.channel_name]
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        print(f"Received: {data}")

        if data['type'] == 'join':
            # Already handled in connect, but kept for fallback
            if self.channel_name not in self.connected_players:
                team = 'A' if len([p for p in self.connected_players.values() if p['team'] == 'A']) < 5 else 'B'
                available_players = [p for p in self.game_state['players'].keys() 
                                   if p.startswith(team) and p not in [cp['player_id'] for cp in self.connected_players.values()]]
                player_id = available_players[0] if available_players else "A_1"
                
                self.connected_players[self.channel_name] = {'player_id': player_id, 'team': team}
                await self.send(json.dumps({
                    'type': 'assign_player',
                    'player_id': player_id,
                    'team': team,
                    'game_state': self.game_state
                }))
        
        elif data['type'] == 'player_move':
            player_id = data['player_id']
            if player_id in self.game_state['players']:
                self.game_state['players'][player_id]['x'] = data['movement']['x']
                self.game_state['players'][player_id]['y'] = data['movement']['y']
                await self.broadcast_state()
        
        elif data['type'] == 'ball_update':
            self.game_state['ball'] = data['ball']
            await self.broadcast_state()
        
        elif data['type'] == 'score_update':
            self.game_state['scores'] = data['scores']
            await self.broadcast_state()

    async def broadcast_state(self):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'state_update',
                'game_state': self.game_state
            }
        )

    async def state_update(self, event):
        await self.send(json.dumps({
            'type': 'state_update',
            'game_state': event['game_state']
        }))
        


import json
import random
from datetime import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import GameRoom, PlayerStatus
from channels.db import database_sync_to_async

class LudoGameConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_group_name = None
        self.game_id = None
        self.game_state = {
            "players": {},
            "current_turn": None,
            "dice": None,
            "status": "waiting",
        }
        self.colors = ["red", "blue", "green", "yellow"]

    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.room_group_name = f"ludo_{self.game_id}"
        self.user = self.scope["user"]

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        await self.initialize_player()
        await self.send_game_state()
        await self.check_game_start()

    async def disconnect(self, close_code):
        if self.user.username in self.game_state["players"]:
            del self.game_state["players"][self.user.username]
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        await self.broadcast_game_state()

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("type")

        if action == "roll_dice":
            await self.handle_dice_roll()
        elif action == "move_piece":
            await self.handle_piece_move(data["piece"], data["new_position"])
        elif action == "chat_message":
            await self.handle_chat_message(data["message"])
        elif action == "player_ready":
            await self.handle_player_ready()

    # Game Logic Handlers
    async def initialize_player(self):
        room = await self.get_game_room()
        player_status = await self.get_or_create_player_status(room)
        
        if self.user.username not in self.game_state["players"]:
            color = await self.assign_color(room)
            self.game_state["players"][self.user.username] = {
                "color": color,
                "pieces": {"piece1": 0, "piece2": 0, "piece3": 0, "piece4": 0},
            }
            if not self.game_state["current_turn"]:
                self.game_state["current_turn"] = self.user.username

    async def handle_dice_roll(self):
        if self.game_state["current_turn"] == self.user.username:
            dice = random.randint(1, 6)
            self.game_state["dice"] = dice
            await self.broadcast_game_state()

    async def handle_piece_move(self, piece, new_position):
        if self.game_state["current_turn"] == self.user.username:
            player = self.game_state["players"][self.user.username]
            if piece in player["pieces"]:
                player["pieces"][piece] = new_position
                self.game_state["dice"] = None  # Reset dice after move
                await self.switch_turn()
                await self.broadcast_game_state()

    async def handle_chat_message(self, message):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "username": self.user.username,
                "message": message,
                "timestamp": datetime.now().isoformat(),
            }
        )

    async def handle_player_ready(self):
        player_status = await self.get_or_create_player_status(await self.get_game_room())
        await self.set_player_ready(player_status)
        await self.check_game_start()

    async def switch_turn(self):
        players = list(self.game_state["players"].keys())
        if not players:
            return
        current_idx = players.index(self.game_state["current_turn"])
        next_idx = (current_idx + 1) % len(players)
        self.game_state["current_turn"] = players[next_idx]

    async def check_game_start(self):
        room = await self.get_game_room()
        if await self.get_player_count(room) >= 2 and await self.all_players_ready(room):  # Adjusted to >= 2 for testing
            self.game_state["status"] = "playing"
            await self.broadcast_game_state()

    # Database Operations (unchanged)
    @database_sync_to_async
    def get_game_room(self):
        return GameRoom.objects.get(room_code=self.game_id)

    @database_sync_to_async
    def get_or_create_player_status(self, room):
        status, created = PlayerStatus.objects.get_or_create(
            user=self.user, game_room=room,
            defaults={"current_position": {"piece1": 0, "piece2": 0, "piece3": 0, "piece4": 0}}
        )
        return status

    @database_sync_to_async
    def set_player_ready(self, player_status):
        player_status.is_ready = True
        player_status.save()

    @database_sync_to_async
    def get_player_count(self, room):
        return room.players.count()

    @database_sync_to_async
    def all_players_ready(self, room):
        return all(status.is_ready for status in PlayerStatus.objects.filter(game_room=room))

    @database_sync_to_async
    def assign_color(self, room):
        used_colors = [status.color for status in PlayerStatus.objects.filter(game_room=room)]
        available_colors = [c for c in self.colors if c not in used_colors]
        color = available_colors[0] if available_colors else "red"
        status = PlayerStatus.objects.get(user=self.user, game_room=room)
        status.color = color
        status.save()
        return color

    # Broadcasting
    async def send_game_state(self):
        await self.send(text_data=json.dumps({
            "type": "game_state",
            "game_state": self.game_state,
            "username": self.user.username,
        }))

    async def broadcast_game_state(self):
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "game_state_update", "game_state": self.game_state}
        )

    # WebSocket Event Handlers
    async def game_state_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "game_state",
            "game_state": event["game_state"],
            "username": self.user.username,
        }))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "chat_message",
            "username": event["username"],
            "message": event["message"],
            "timestamp": event["timestamp"],
        }))        