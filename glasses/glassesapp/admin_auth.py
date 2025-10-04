from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from .admin_site import admin_site

# Register User and Group models with custom admin site
admin_site.register(User, UserAdmin)
admin_site.register(Group, GroupAdmin) 