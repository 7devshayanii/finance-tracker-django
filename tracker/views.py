"""
Views for the Finance Tracking System.

Handles all page rendering: dashboard, transaction CRUD, filtering,
CSV export, and authentication (register/login/logout).
"""

import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.utils import timezone

from .models import Transaction
from .forms import TransactionForm, TransactionFilterForm, CustomUserCreationForm
from .services import (
    get_total_income,
    get_total_expenses,
    get_balance,
    get_category_breakdown,
    get_monthly_summary,
    get_recent_transactions,
    get_transaction_count,
    filter_transactions,
)
from .decorators import role_required, get_user_role


# ---------------------------------------------------------------------------
# Authentication Views
# ---------------------------------------------------------------------------

def register_view(request):
    """Handle user registration. New users are assigned the 'Viewer' role."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Automatic profile creation handled via models.Profile post_save signal
            login(request, user)
            messages.success(request, f'Welcome, {user.username}! Your account has been created.')
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()

    return render(request, 'tracker/register.html', {'form': form})


def logout_view(request):
    """Handle user logout cleanly via GET mapping."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
@role_required(['Viewer', 'Analyst', 'Admin'])
def dashboard_view(request):
    """
    Main dashboard — shows financial summaries, category breakdowns,
    monthly trends, and recent transactions.
    """
    qs = Transaction.objects.all()

    context = {
        'total_income': get_total_income(qs),
        'total_expenses': get_total_expenses(qs),
        'balance': get_balance(qs),
        'category_breakdown': get_category_breakdown(qs),
        'monthly_summary': get_monthly_summary(qs),
        'recent_transactions': get_recent_transactions(qs, limit=5),
        'transaction_count': get_transaction_count(qs),
    }
    return render(request, 'tracker/dashboard.html', context)


# ---------------------------------------------------------------------------
# Transaction List (with filtering, search, pagination)
# ---------------------------------------------------------------------------

@login_required
@role_required(['Viewer', 'Analyst', 'Admin'])
def transaction_list_view(request):
    """
    List all transactions with optional filtering.
    Analysts and Admins can use the filter panel; Viewers see unfiltered list.
    """
    qs = Transaction.objects.all()
    user_role = get_user_role(request.user)

    filter_form = TransactionFilterForm(request.GET or None)

    # Apply filters only for Analyst/Admin roles
    if user_role in ['Analyst', 'Admin'] and filter_form.is_valid():
        filters = {
            'date_from': filter_form.cleaned_data.get('date_from'),
            'date_to': filter_form.cleaned_data.get('date_to'),
            'type': filter_form.cleaned_data.get('type'),
            'category': filter_form.cleaned_data.get('category'),
            'search': filter_form.cleaned_data.get('search'),
        }
        qs = filter_transactions(qs, filters)

    # Pagination — 10 transactions per page
    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'filter_form': filter_form,
        'total_results': paginator.count,
    }
    return render(request, 'tracker/transaction_list.html', context)


# ---------------------------------------------------------------------------
# Transaction CRUD
# ---------------------------------------------------------------------------

@login_required
@role_required(['Admin'])
def transaction_create_view(request):
    """Create a new transaction. Only Admins can access this."""
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.save()
            messages.success(request, 'Transaction created successfully.')
            return redirect('transaction_list')
    else:
        form = TransactionForm()

    return render(request, 'tracker/transaction_form.html', {
        'form': form,
        'title': 'Add Transaction',
        'submit_label': 'Create',
    })


@login_required
@role_required(['Admin'])
def transaction_update_view(request, pk):
    """Update an existing transaction. Only Admins can access this."""
    transaction = get_object_or_404(Transaction, pk=pk)

    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transaction updated successfully.')
            return redirect('transaction_list')
    else:
        form = TransactionForm(instance=transaction)

    return render(request, 'tracker/transaction_form.html', {
        'form': form,
        'title': 'Edit Transaction',
        'submit_label': 'Update',
    })


@login_required
@role_required(['Admin'])
def transaction_delete_view(request, pk):
    """Confirm and delete a transaction. Only Admins can access this."""
    transaction = get_object_or_404(Transaction, pk=pk)

    if request.method == 'POST':
        transaction.delete()
        messages.success(request, 'Transaction deleted successfully.')
        return redirect('transaction_list')

    return render(request, 'tracker/transaction_confirm_delete.html', {
        'transaction': transaction,
    })


# ---------------------------------------------------------------------------
# CSV Export
# ---------------------------------------------------------------------------

@login_required
@role_required(['Analyst', 'Admin'])
def export_csv_view(request):
    """Export all transactions as a CSV file."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="transactions_{timezone.now().strftime("%Y%m%d")}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow(['Date', 'Type', 'Category', 'Amount', 'Description', 'User'])

    transactions = Transaction.objects.all().order_by('-date')
    for t in transactions:
        writer.writerow([
            t.date,
            t.get_type_display(),
            t.get_category_display(),
            t.amount,
            t.description,
            t.user.username,
        ])

    return response



from django.http import HttpResponse
from django.contrib.auth.models import User

def create_user_temp(request):
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser("admin", "admin@gmail.com", "admin123")
    return HttpResponse("User created")