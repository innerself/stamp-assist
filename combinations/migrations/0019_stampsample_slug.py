# Generated by Django 4.2.1 on 2023-07-25 07:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('combinations', '0018_stampsample_url_alter_desk_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='stampsample',
            name='slug',
            field=models.SlugField(default=''),
            preserve_default=False,
        ),
    ]
