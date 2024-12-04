# models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    # Adding custom fields to the user model
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(unique=True)

    # You can also add any other custom fields if needed
    # Example: A field to store the user's phone number
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return self.username  # or return self.email or any field you want to represent the user
