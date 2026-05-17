# Intelligence / feature fields on daily rollup

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("smartagile", "0016_usage_daily_rollup"),
    ]

    operations = [
        migrations.AddField(
            model_name="usagedailyrollup",
            name="distracted_duration_seconds",
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name="usagedailyrollup",
            name="app_switch_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="usagedailyrollup",
            name="deep_work_segment_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="usagedailyrollup",
            name="focus_score",
            field=models.FloatField(blank=True, null=True),
        ),
    ]
