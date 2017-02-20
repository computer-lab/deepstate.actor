from django.db import models


class Team(models.Model):
    slack_id = models.CharField(max_length=512, unique=True)
    name = models.CharField(max_length=512)
    token = models.CharField(max_length=512)
    active = models.BooleanField(default=True)
