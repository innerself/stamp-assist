# Generated by Django 4.2.1 on 2023-05-27 11:11

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('combinations', '0004_desk_stamp_desk'),
    ]

    operations = [
        migrations.CreateModel(
            name='StampSample',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('year', models.PositiveSmallIntegerField()),
                ('country', models.CharField(max_length=255)),
                ('value', models.DecimalField(decimal_places=2, max_digits=10)),
                ('width', models.PositiveSmallIntegerField(null=True)),
                ('height', models.PositiveSmallIntegerField(null=True)),
                ('topics', models.JSONField(default=list)),
                ('michel_number', models.CharField(blank=True, max_length=255, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='UserStamp',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('comment', models.CharField(max_length=255)),
                ('quantity', models.PositiveSmallIntegerField()),
            ],
        ),
        migrations.RemoveField(
            model_name='stamp',
            name='name',
        ),
        migrations.RemoveField(
            model_name='stamp',
            name='topic',
        ),
        migrations.RemoveField(
            model_name='stamp',
            name='value',
        ),
        migrations.AlterField(
            model_name='desk',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='desk', to=settings.AUTH_USER_MODEL),
        ),
        migrations.DeleteModel(
            name='StampBlock',
        ),
        migrations.AddField(
            model_name='userstamp',
            name='desk',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='user_stamps', to='combinations.desk'),
        ),
        migrations.AddField(
            model_name='userstamp',
            name='sample',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='combinations.stampsample'),
        ),
        migrations.AddField(
            model_name='userstamp',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='userstamp',
            unique_together={('sample', 'user')},
        ),
    ]
