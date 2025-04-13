from django.urls import path
from . import views




urlpatterns = [
    path('', views.home, name='home'),
    path('game_room/<int:game_id>/', views.game_room_views, name='game_room_views'),
    #path('game/<str:game_id>/', views.game_room_views, name='game_room'),

    path('game_lobby/<str:room_code>/<str:game_id>/', views.game_lobby, name='game_lobby'),  # Include game_code in the URL
    path('start_game/<str:room_code>/<str:game_id>/', views.start_game, name='start_game'),  # Include game_code in the URL
    path('chess/<str:room_code>', views.chess, name='chess'),
    # path('agar/', views.agar, name='agar'),
    path('snake/<str:room_code>', views.snake, name='snake'),
<<<<<<< HEAD
    path('get_players/<str:room_code>/', views.get_players, name='get_players')
=======
    path('ludo/<str:room_code>',views.ludo, name='ludo'),
    path('get_players/<str:room_code>/', views.get_players, name='get_players'),
     path('check_game_starting/<str:room_code>/', views.check_game_starting, name='check_game_starting'),
    path('start_game_countdown/<str:room_code>/<str:game_id>/', views.start_game_countdown, name='start_game_countdown'),
    # ... your other URL patterns ...

>>>>>>> 3139c241f10c3e9062b3f79bb2e1d916f9630e1f
]



