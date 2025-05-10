from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ClinicSubscription, ClinicSubscriptionHistory

@receiver(post_save, sender=ClinicSubscription)
def create_subscription_history(sender, instance, **kwargs):
    ClinicSubscriptionHistory.objects.create(
        clinic=instance.clinic,
        plan=instance.plan,
        start_date=instance.start_date,
        end_date=instance.end_date,
        price=instance.plan.price,
        discount=instance.discount,
        paid_amount=instance.plan.price * (1 - (int(instance.discount.strip('%')) / 100)) if instance.discount else instance.plan.price,
        status='active' if instance.end_date >= instance.start_date else 'expired'
    )