from rest_framework import serializers
from .models import BirdSound, Bird


class BirdSoundFilenameSerializer(serializers.ModelSerializer):
    class Meta:
        model = BirdSound
        fields = ['filename']

class BirdSoundSerializer(serializers.ModelSerializer):
    class Meta:
        model = BirdSound
        fields = ['id', 'filename', 'eBird', 'secondary_labels', 'station', 
                 'recording_mode', 'recording_datetime', 'file_type', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class BirdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bird
        fields = ['eBird', 'common_name', 'scientific_name', 'extra_name', 'created_at', 'updated_at']
        read_only_fields = ['eBird', 'created_at', 'updated_at']

class BirdListFilterSerializer(serializers.Serializer):
    random = serializers.BooleanField(required=False, allow_null=True, default=False)
    #quantity = -1, cancel pagination and dump all
    quantity = serializers.IntegerField(required=False, allow_null=True, default=3)


class BirdSoundFilterSerializer(serializers.Serializer):
    station = serializers.CharField(required=False, allow_null=True, max_length=50)
    recording_mode = serializers.CharField(required=False, allow_null=True, max_length=50)
    start_time = serializers.DateTimeField(required=False, allow_null=True, input_formats=['iso-8601'])
    end_time = serializers.DateTimeField(required=False, allow_null=True, input_formats=['iso-8601'])
    
    def validate(self, data):
        if data.get('start_time') and data.get('end_time'):
            if data['start_time'] > data['end_time']:
                raise serializers.ValidationError("start_time must be before end_time")
        return data