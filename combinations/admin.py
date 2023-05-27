from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User
from .models import StampCollection, StampSample, UserStamp

admin.site.register(User, UserAdmin)
admin.site.register(StampSample)
admin.site.register(UserStamp)
admin.site.register(StampCollection)
