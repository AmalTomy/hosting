# Generated by Django 5.0.6 on 2024-08-28 12:45

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0011_feedback_bus_name_feedback_bus_route_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='feedback',
            name='bus',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='feedbacks', to='home.bus'),
        ),
    ]
