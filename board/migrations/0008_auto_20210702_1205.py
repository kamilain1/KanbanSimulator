# Generated by Django 3.0.7 on 2021-07-02 09:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('board', '0007_room_version'),
    ]

    operations = [
        migrations.AlterField(
            model_name='player',
            name='spectator',
            field=models.BooleanField(default=False, verbose_name='Является ли игрок наблюдателем'),
        ),
        migrations.AlterField(
            model_name='player',
            name='team',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='board.Team', verbose_name='Команда игрока'),
        ),
    ]
