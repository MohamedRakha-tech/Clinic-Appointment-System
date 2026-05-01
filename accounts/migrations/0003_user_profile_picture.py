from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_alter_patientprofile_address_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="profile_picture",
            field=models.ImageField(blank=True, null=True, upload_to="profile_pictures/"),
        ),
    ]
