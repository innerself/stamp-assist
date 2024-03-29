# Generated by Django 4.2.1 on 2023-05-26 09:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('combinations', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='stamp',
            name='collection',
        ),
        migrations.CreateModel(
            name='StampBlock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.IntegerField(default=1)),
                ('collection', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='combinations.stampcollection')),
                ('stamp', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='combinations.stamp')),
            ],
        ),
    ]
