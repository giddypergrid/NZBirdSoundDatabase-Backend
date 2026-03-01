from django.http import JsonResponse, FileResponse
from django.conf import settings
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema
from pathlib import Path
from .models import BirdSound, Bird
from .serializers import BirdSoundSerializer, BirdSerializer, BirdSoundFilenameSerializer, BirdSoundFilterSerializer, BirdListFilterSerializer

# ****************** General Endpoints ******************
class BirdListPagination(PageNumberPagination):
    page_size = 10

class BirdSoundById(generics.RetrieveAPIView):
    """
    GET /birds/api/sounds/{id}/
    """
    queryset = BirdSound.objects.all()
    serializer_class = BirdSoundSerializer

class BirdById(generics.RetrieveAPIView):
    """
    GET /birds/api/birds/{id}/
    """
    queryset = Bird.objects.all()
    serializer_class = BirdSerializer

class BirdList(generics.ListAPIView):
    pagination_class = BirdListPagination
    serializer_class = BirdSerializer

    @extend_schema(parameters=[BirdListFilterSerializer])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Bird.objects.all()
        filter_serializer = BirdListFilterSerializer(data=self.request.query_params)
        filter_serializer.is_valid(raise_exception=True)
        
        validated_data = filter_serializer.validated_data
        
        if validated_data.get('random'):
            queryset = queryset.order_by('?')
        
        quantity = validated_data.get('quantity')
        if quantity == -1:
            self.pagination_class = None
        elif quantity:
            queryset = queryset[:quantity]
        
        return queryset
# *****************************************************

# ****************** Audio Endpoints ******************
class BirdSoundList(generics.ListAPIView):
    serializer_class = BirdSoundSerializer

    def get_queryset(self):
        queryset = BirdSound.objects.all()
        eBird = self.kwargs.get('primary_label')
        if eBird:
            print(f"Searching for audio with label: '{eBird}'")
            queryset = queryset.filter(eBird__iexact=eBird)
            print(f"Found {queryset.count()} records")

        filter_serializer = BirdSoundFilterSerializer(data=self.request.query_params)
        filter_serializer.is_valid(raise_exception=True)
        
        validated_data = filter_serializer.validated_data
        station = validated_data.get('station')
        if station:
            queryset = queryset.filter(station=station)
            
        recording_mode = validated_data.get('recording_mode')
        if recording_mode:
            queryset = queryset.filter(recording_mode=recording_mode)

        start_time = validated_data.get('start_time')
        if start_time:
            queryset = queryset.filter(recording_datetime__gte=start_time)

        end_time = validated_data.get('end_time')
        if end_time:
            queryset = queryset.filter(recording_datetime__lte=end_time)
        
        return queryset

class AudioFileView(APIView):
    """
    GET /birds/api/audio/{eBird}/{filename}/
    Serve audio file by filename (which already includes path from AUDIO_FILES_ROOT)
    """
    def get(self, request, eBird, filename):
        from pathlib import Path
        
        # filename already includes the full path from AUDIO_FILES_ROOT
        # e.g., "ausbit1/DE76_BIRX_131008_034239_006.flac"
        file_path = Path(settings.AUDIO_FILES_ROOT) / eBird / filename
        
        try:
            file_path.resolve().relative_to(Path(settings.AUDIO_FILES_ROOT).resolve())
        except ValueError:
            raise PermissionDenied("Invalid file path")
        
        if not file_path.exists():
            raise NotFound("File not found")
        
        from mimetypes import guess_type
        content_type, encoding = guess_type(str(file_path))
        if content_type is None:
            content_type = 'application/octet-stream'
        
        return FileResponse(open(file_path, 'rb'), content_type=content_type)

# *****************************************************

# ****************** Import Endpoints ******************
class ImageFileView(APIView):
    """
    GET /birds/api/image/{common_name}/{index}/
    Serve image file by common_name (folder) and index
    """
    def get(self, request, common_name, index):
        from mimetypes import guess_type

        normalized_common_name = common_name.replace(" ", "_")
        file_path = Path(settings.IMAGE_FILES_ROOT) / normalized_common_name / f"{index}.jpeg"
        
        try:
            file_path.resolve().relative_to(Path(settings.IMAGE_FILES_ROOT).resolve())
        except ValueError:
            raise PermissionDenied("Invalid file path")
        
        if not file_path.exists():
            raise NotFound("File not found")
        
        content_type, encoding = guess_type(str(file_path))
        if content_type is None:
            content_type = 'application/octet-stream'
        
        return FileResponse(open(file_path, 'rb'), content_type=content_type)