from django.db import models


class CollectionModel(models.Model):

    filename = models.CharField(max_length=128)
    created = models.DateTimeField(auto_now_add=True)
