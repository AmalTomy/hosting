# Generated by Django 5.0.6 on 2024-08-25 07:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='driversinfo',
            name='email',
            field=models.EmailField(max_length=254, unique=True),
        ),
    ]
