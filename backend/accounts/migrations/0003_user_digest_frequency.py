from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_alter_user_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='digest_frequency',
            field=models.CharField(
                choices=[('off', 'Off'), ('daily', 'Daily'), ('weekly', 'Weekly')],
                default='off',
                max_length=10,
            ),
        ),
    ]
