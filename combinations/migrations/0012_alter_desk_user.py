# Generated by Django 4.2.1 on 2023-06-28 20:29

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('combinations', '0011_desk_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='desk',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='desks', to=settings.AUTH_USER_MODEL),
        ),
    ]