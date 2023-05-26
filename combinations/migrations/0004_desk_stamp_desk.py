# Generated by Django 4.2.1 on 2023-05-26 13:31

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('combinations', '0003_alter_stampblock_collection'),
    ]

    operations = [
        migrations.CreateModel(
            name='Desk',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='stamp',
            name='desk',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='combinations.desk'),
        ),
    ]
