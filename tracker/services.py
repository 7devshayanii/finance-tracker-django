"""
Services module — business logic for the Finance Tracking System.

Keeps analytics and computation logic out of views and templates.
All summary/aggregation functions live here for clean separation of concerns.
"""

from django.db.models import Sum, Q
from django.db.models.functions import TruncMonth
from decimal import Decimal
from .models import Transaction


def get_total_income(queryset=None):
    """Calculate total income from a queryset of transactions."""
    if queryset is None:
        queryset = Transaction.objects.all()
    result = queryset.filter(type=Transaction.INCOME).aggregate(
        total=Sum('amount')
    )
    return result['total'] or Decimal('0.00')


def get_total_expenses(queryset=None):
    """Calculate total expenses from a queryset of transactions."""
    if queryset is None:
        queryset = Transaction.objects.all()
    result = queryset.filter(type=Transaction.EXPENSE).aggregate(
        total=Sum('amount')
    )
    return result['total'] or Decimal('0.00')


def get_balance(queryset=None):
    """Calculate current balance (income - expenses)."""
    income = get_total_income(queryset)
    expenses = get_total_expenses(queryset)
    return income - expenses


def get_category_breakdown(queryset=None):
    """
    Get a breakdown of spending/earning by category.
    Returns a list of dicts with category name, total amount, and type.
    """
    if queryset is None:
        queryset = Transaction.objects.all()

    # Expense breakdown
    expense_breakdown = (
        queryset
        .filter(type=Transaction.EXPENSE)
        .values('category')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )

    # Income breakdown
    income_breakdown = (
        queryset
        .filter(type=Transaction.INCOME)
        .values('category')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )

    # Map category keys to display names
    category_map = dict(Transaction.CATEGORY_CHOICES)

    expense_data = [
        {
            'category': category_map.get(item['category'], item['category']),
            'total': item['total'],
            'type': 'Expense',
        }
        for item in expense_breakdown
    ]

    income_data = [
        {
            'category': category_map.get(item['category'], item['category']),
            'total': item['total'],
            'type': 'Income',
        }
        for item in income_breakdown
    ]

    return {'expenses': expense_data, 'income': income_data}


def get_monthly_summary(queryset=None):
    """
    Get monthly totals for income and expenses.
    Returns a list of dicts with month, income total, expense total, and net.
    """
    if queryset is None:
        queryset = Transaction.objects.all()

    # Get all months that have transactions
    months = (
        queryset
        .annotate(month=TruncMonth('date'))
        .values('month')
        .distinct()
        .order_by('-month')
    )

    monthly_data = []
    for month_entry in months:
        month = month_entry['month']
        month_qs = queryset.filter(
            date__year=month.year,
            date__month=month.month
        )
        income = get_total_income(month_qs)
        expenses = get_total_expenses(month_qs)
        monthly_data.append({
            'month': month,
            'income': income,
            'expenses': expenses,
            'net': income - expenses,
        })

    return monthly_data


def get_recent_transactions(queryset=None, limit=5):
    """Get the most recent transactions."""
    if queryset is None:
        queryset = Transaction.objects.all()
    return queryset.order_by('-date', '-created_at')[:limit]


def get_transaction_count(queryset=None):
    """Get total number of transactions."""
    if queryset is None:
        queryset = Transaction.objects.all()
    return queryset.count()


def filter_transactions(queryset, filters):
    """
    Apply filters to a transaction queryset.
    Accepts a dict of filter params (date_from, date_to, type, category, search).
    """
    if filters.get('date_from'):
        queryset = queryset.filter(date__gte=filters['date_from'])
    if filters.get('date_to'):
        queryset = queryset.filter(date__lte=filters['date_to'])
    if filters.get('type'):
        queryset = queryset.filter(type=filters['type'])
    if filters.get('category'):
        queryset = queryset.filter(category=filters['category'])
    if filters.get('search'):
        queryset = queryset.filter(
            Q(description__icontains=filters['search'])
        )
    return queryset
