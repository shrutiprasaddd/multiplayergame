from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('game_room/<int:game_id>/', views.game_room_views, name='game_room_views'),

    path('game_lobby/<str:room_code>/<str:game_id>/', views.game_lobby, name='game_lobby'),  # Include game_code in the URL
    path('start_game/<str:room_code>/<str:game_id>/', views.start_game, name='start_game'),  # Include game_code in the URL
    path('chess/<str:room_code>', views.chess, name='chess'),
    # path('agar/', views.agar, name='agar'),
    path('snake/<str:room_code>', views.snake, name='snake'),
]
