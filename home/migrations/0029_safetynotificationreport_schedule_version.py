# Generated by Django 5.0.6 on 2024-10-09 14:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0028_agentjob_original_arrival_date_alter_agentjob_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='safetynotificationreport',
            name='schedule_version',
            field=models.IntegerField(blank=True, default=1, null=True),
        ),
    ]
