# Generated by Django 4.2.1 on 2023-06-30 17:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('combinations', '0012_alter_desk_user'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='stampcollection',
            name='user',
        ),
        migrations.AddField(
            model_name='userstamp',
            name='user_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.DeleteModel(
            name='Stamp',
        ),
        migrations.DeleteModel(
            name='StampCollection',
        ),
    ]
