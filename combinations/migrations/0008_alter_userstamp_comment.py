# Generated by Django 4.2.1 on 2023-05-28 18:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('combinations', '0007_alter_stampsample_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userstamp',
            name='comment',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]