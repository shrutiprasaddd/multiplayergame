import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import GameRoom, PlayerStatus
from django.contrib.auth.models import User
from channels.db import database_sync_to_async

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code']

        # Get the game room from the database
        self.game_room = await self.get_game_room(self.room_code)
        self.user = self.scope["user"]

        # Ensure the user is part of the game room
        if not await self.is_user_in_game(self.user, self.game_room):
            await self.close()
            return

        self.room_group_name = f"game_{self.room_code}"

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        # Accept the WebSocket connection
        await self.accept()

        # Notify all players about the new connection
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'player_join',  # Type of message
                'player': self.user.username,
            }
        )

    @database_sync_to_async
    def get_game_room(self, room_code):
        print(room_code)
        return GameRoom.objects.get(room_code=room_code)

    @database_sync_to_async
    def is_user_in_game(self, user, game_room):
        return user in game_room.players.all()

    @database_sync_to_async
    def get_player_status(self, user, game_room):
        return PlayerStatus.objects.get(user=user, game_room=game_room)

    async def disconnect(self, close_code):
        # Leave room group when player disconnects
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('type')

        if action == 'move':
            # Extract move details
            move = data['move']
            board = data['board']

            # Broadcast updated board and move to all players
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chess_move_update',
                    'player': self.user.username,
                    'move': move,
                    'board': board,  # Send the updated board
                }
            )

        elif action == 'update_score':
            # Update score and send leaderboard update
            player_status = await self.get_player_status(self.user, self.game_room)
            player_status.score += int(data['score'])
            player_status.save()

            leaderboard = [
                {'username': player.user.username, 'score': player.score}
                for player in PlayerStatus.objects.filter(game_room=self.game_room).order_by('-score')
            ]
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'leaderboard_update',
                    'leaderboard': leaderboard,
                }
            )

        elif data.get('type') == 'move':
            # Handle move (broadcast to all connected players)
            move = data['move']
            print("consumer.py move: ",move)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'game_event',
                    'message': f"Move {move} made by {self.user.username}"
                }
            )

        elif data.get('type') == 'chat_message':
            # Broadcast chat message to all players in the room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': data['message']
                }
            )

    async def player_join(self, event):
        # Handle the 'player_join' message type
        await self.send(text_data=json.dumps({
            'type': 'player_join',
            'player': event['player'],
        }))

    async def chess_move_update(self, event):
        # Send the updated board state to all players
        await self.send(text_data=json.dumps({
            'type': 'chess_move_update',
            'player': event['player'],
            'move': event['move'],
            'board': event['board'],  # Ensure board is broadcasted
        }))

    async def leaderboard_update(self, event):
        # Send updated leaderboard to players
        await self.send(text_data=json.dumps({
            'type': 'leaderboard_update',
            'leaderboard': event['leaderboard'],
        }))

    async def game_event(self, event):
        # Handle game event (e.g., move made by player)
        message = event['message']
        await self.send(text_data=json.dumps({
            'type': 'game_event',
            'message': message
        }))

    async def chat_message(self, event):
        # Broadcast chat message to players
        message = event['message']
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': message
        }))

    async def update_snakes(self, event):
        await self.send(text_data=json.dumps({
            'type': 'update',
            'snakes': event['snakes'],
            'player': event['player'],
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

