from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scheduling", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="doctorweeklyschedule",
            name="chk_day_of_week",
        ),
        migrations.AddConstraint(
            model_name="doctorweeklyschedule",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("day_of_week__gte", 0),
                    ("day_of_week__lte", 6),
                ),
                name="chk_day_of_week",
            ),
        ),
    ]
