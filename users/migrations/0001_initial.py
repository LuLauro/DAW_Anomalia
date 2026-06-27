from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("salas", "0002_sala_coordinator"),
    ]

    operations = [
        migrations.CreateModel(
            name="PerfilCoordenador",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="perfil_coordenador",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="coordenador",
                    ),
                ),
                (
                    "salas",
                    models.ManyToManyField(
                        blank=True,
                        related_name="perfis_coordenador",
                        to="salas.sala",
                        verbose_name="salas",
                    ),
                ),
            ],
            options={
                "verbose_name": "Perfil de coordenador",
                "verbose_name_plural": "Perfis de coordenador",
            },
        ),
    ]
