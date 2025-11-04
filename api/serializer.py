# serializers.py
from rest_framework import serializers


class CoordinateSerializer(serializers.Serializer):
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    system = serializers.CharField(default='WGS84', read_only=True)


class UTMCoordinateSerializer(serializers.Serializer):
    zone = serializers.IntegerField(min_value=1, max_value=60)
    letter = serializers.CharField(max_length=1)
    easting = serializers.FloatField()
    northing = serializers.FloatField()
    system = serializers.CharField(default='UTM', read_only=True)


class WebMercatorSerializer(serializers.Serializer):
    x = serializers.FloatField()
    y = serializers.FloatField()
    system = serializers.CharField(default='Web Mercator', read_only=True)


class DistanceCalculationSerializer(serializers.Serializer):
    point1_lat = serializers.FloatField()
    point1_lon = serializers.FloatField()
    point2_lat = serializers.FloatField()
    point2_lon = serializers.FloatField()
    unit = serializers.ChoiceField(choices=['km', 'miles', 'meters'], default='km')


class BoundingBoxSerializer(serializers.Serializer):
    center_lat = serializers.FloatField()
    center_lon = serializers.FloatField()
    radius_km = serializers.FloatField(min_value=0)
