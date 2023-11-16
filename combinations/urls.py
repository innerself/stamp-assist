from django.urls import path

from . import views

app_name = 'combinations'

urlpatterns = [
    path('', views.index_view),
    path('samples/', views.stamp_samples_view, name='samples'),
    # path('samples/', views.StampSampleColnectView.as_view(), name='samples'),
    path('samples/colnect/', views.samples_create_from_colnect_view),
    path('user-stamps/', views.user_stamps_list_view, name='user-stamps'),
    path('user-stamps/add/<int:sample_id>/', views.user_stamp_add_view, name='user-stamp-add'),
    path('user-stamps/<int:stamp_id>/', views.user_stamps_edit_view, name='user-stamp-edit'),
    path('combinations/', views.combinations_view, name='combinations'),
    path('combinations/stick/', views.stick_stamps_to_postcard, name='stick_stamps'),
]
