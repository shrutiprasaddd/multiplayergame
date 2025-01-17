from django.db import models
from django.conf import settings  # To use AUTH_USER_MODEL

class Video(models.Model):
    title = models.CharField(max_length=200)
    url = models.URLField()
    reward = models.DecimalField(max_digits=10, decimal_places=2)  # Reward per view
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.user.username}'s Wallet"

class Transaction(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_withdrawal = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{'Withdrawal' if self.is_withdrawal else 'Earning'}: {self.amount}"
