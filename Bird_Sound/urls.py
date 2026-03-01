from django.urls import path
from . import views

urlpatterns = [
    path('api/sounds/<int:pk>/', views.BirdSoundById.as_view(), name='bird_sound_by_id'),
    path('api/sounds/bird-label/<str:primary_label>/', views.BirdSoundList.as_view(), name='bird_sound_list_by_bird'),
    path('api/birds/<str:pk>/', views.BirdById.as_view(), name='bird_by_id'),
    path('api/birds/', views.BirdList.as_view(), name='bird_list'),
    path('api/audio/<str:eBird>/<str:filename>/', views.AudioFileView.as_view(), name='audio_file'),
    path('api/image/<str:common_name>/<int:index>/', views.ImageFileView.as_view(), name='image_file'),
]
