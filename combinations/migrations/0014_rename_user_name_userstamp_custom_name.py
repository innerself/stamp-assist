# Generated by Django 4.2.1 on 2023-06-30 17:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('combinations', '0013_remove_stampcollection_user_userstamp_user_name_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='userstamp',
            old_name='user_name',
            new_name='custom_name',
        ),
    ]