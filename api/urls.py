# urls.py
from django.urls import path
from views import ConvertToWebMercatorView,ConvertToUTMView,ConvertFromWebMercatorView,CalculateDistanceView,BoundingBoxView,batch_convert_view,coordinate_info_view
urlpatterns = [
    path('api/coordinates/convert/web-mercator/', ConvertToWebMercatorView.as_view()),
    path('api/coordinates/convert/utm/', ConvertToUTMView.as_view()),
    path('api/coordinates/convert/from-web-mercator/', ConvertFromWebMercatorView.as_view()),
    path('api/coordinates/distance/', CalculateDistanceView.as_view()),
    path('api/coordinates/bounding-box/', BoundingBoxView.as_view()),
    path('api/coordinates/batch-convert/', batch_convert_view),
    path('api/coordinates/info/', coordinate_info_view),
]