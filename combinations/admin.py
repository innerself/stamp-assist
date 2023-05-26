from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User
from .models import Stamp, StampBlock, StampCollection

admin.site.register(User, UserAdmin)
admin.site.register(Stamp)
admin.site.register(StampBlock)
admin.site.register(StampCollection)
