"""
Models for the Finance Tracking System.

Defines the Transaction model which stores all financial records
(income and expenses) with category tagging and date tracking.
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    """
    User Profile to explicitly store roll-based access permissions.
    """
    ROLE_CHOICES = [
        ('Admin', 'Admin'),
        ('Analyst', 'Analyst'),
        ('Viewer', 'Viewer'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='Viewer')

    def __str__(self):
        return f"{self.user.username} - {self.role}"


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Automatically create a Viewer profile for newly created users."""
    if created:
        Profile.objects.create(user=instance, role='Viewer')
    else:
        # Save the profile if it exists when user is saved
        if hasattr(instance, 'profile'):
            instance.profile.save()

class Transaction(models.Model):
    """
    Represents a single financial transaction (income or expense).
    Each transaction is linked to a user who created it.
    """

    # Transaction type choices
    INCOME = 'income'
    EXPENSE = 'expense'
    TYPE_CHOICES = [
        (INCOME, 'Income'),
        (EXPENSE, 'Expense'),
    ]

    # Category choices for transactions
    CATEGORY_CHOICES = [
        ('salary', 'Salary'),
        ('freelance', 'Freelance'),
        ('investment', 'Investment'),
        ('food', 'Food & Dining'),
        ('rent', 'Rent & Housing'),
        ('utilities', 'Utilities'),
        ('transport', 'Transportation'),
        ('entertainment', 'Entertainment'),
        ('healthcare', 'Healthcare'),
        ('education', 'Education'),
        ('shopping', 'Shopping'),
        ('travel', 'Travel'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='transactions',
        help_text='The user who created this transaction.'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Transaction amount (must be positive).'
    )
    type = models.CharField(
        max_length=7,
        choices=TYPE_CHOICES,
        help_text='Whether this is an income or expense.'
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        help_text='Category of the transaction.'
    )
    date = models.DateField(
        help_text='Date of the transaction.'
    )
    description = models.TextField(
        blank=True,
        default='',
        help_text='Optional notes or description for the transaction.'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'

    def __str__(self):
        return f"{self.get_type_display()} - {self.get_category_display()} - ₹{self.amount}"
