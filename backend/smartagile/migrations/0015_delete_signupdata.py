from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0013_alter_user_fks_to_accounts_user"),
        ("smartagile", "0014_alter_events_fk_to_accounts_user"),
    ]

    operations = [
        migrations.DeleteModel(
            name="SignupData",
        ),
    ]
