from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("salas", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="sala",
            name="coordinator",
            field=models.ForeignKey(
                blank=True,
                help_text="Coordenador responsavel por esta sala.",
                null=True,
                on_delete=models.SET_NULL,
                related_name="salas_coordenadas",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
