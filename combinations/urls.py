from django.urls import path

from . import views

app_name = 'combinations'

urlpatterns = [
    path('', views.root_view),
    path('samples/', views.StampSampleListView.as_view()),
    path('samples/colnect/', views.samples_create_from_colnect_view),
]
