from django.urls import path
from . import views

urlpatterns = [
    path('', views.video_list, name='video_list'),
    path('watch/<int:video_id>/', views.watch_video, name='watch_video'),
    path('wallet/', views.wallet, name='wallet'),
    path('withdraw/', views.withdraw, name='withdraw'),
]
