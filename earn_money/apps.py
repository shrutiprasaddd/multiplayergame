from django.apps import AppConfig

class EarnMoneyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "earn_money"

    def ready(self):
        import earn_money.signals  # Import the signals module
