from django.urls import path

from . import views

app_name = 'combinations'

urlpatterns = [
    path('', views.root_view),
    path('samples/', views.StampSampleColnectView.as_view(), name='samples'),
    path('samples/colnect/', views.samples_create_from_colnect_view),
    path('user-stamps/', views.user_stamp_view, name='user-stamps'),
    path('user-stamps/<int:stamp_id>/', views.user_stamp_edit_view, name='user-stamp-edit'),
    path('combinations/', views.combinations_view, name='combinations'),
]
