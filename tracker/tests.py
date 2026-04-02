"""
Comprehensive test suite for the Finance Tracking System.

Covers:
  1. Transaction Model (CRUD + validation)
  2. Filtering Logic (type, date range, category)
  3. Summary & Analytics Services
  4. User Roles (Viewer / Analyst / Admin)
  5. Authentication & Access Control
  6. Form Validation & Error Handling
  7. Database Behaviour
  8. UI / Page Flow (redirects and response codes)
  9. Edge Cases (zero records, only expenses, large dataset, same-date entries)
"""

from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError

from .models import Transaction
from .forms import TransactionForm
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


def make_user(username, role=None, password="pass1234"):
    """Create a test user and optionally assign a role."""
    user = User.objects.create_user(username=username, password=password)
    # The post_save signal automatically gives them a 'Viewer' profile.
    if role:
        user.profile.role = role
        user.profile.save()
    return user


def make_transaction(user, amount="1000.00", t_type="income",
                     category="salary", dt=None, description=""):
    """Shortcut to create a Transaction for tests."""
    return Transaction.objects.create(
        user=user,
        amount=Decimal(amount),
        type=t_type,
        category=category,
        date=dt or date.today(),
        description=description,
    )


# ===========================================================================
# 1. TRANSACTION CRUD (Model & Form Level)
# ===========================================================================

class TransactionModelCRUDTest(TestCase):
    """Tests for creating, reading, updating, and deleting transactions."""

    def setUp(self):
        self.user = make_user("testuser", role="Admin")

    # -------------------------------------------------------------------
    # CREATE
    # -------------------------------------------------------------------

    def test_create_valid_transaction(self):
        """Valid data → transaction saved with correct values."""
        t = make_transaction(self.user, amount="1000.00", t_type="income")
        self.assertEqual(t.amount, Decimal("1000.00"))
        self.assertEqual(t.type, "income")
        self.assertIsNotNone(t.pk)

    def test_create_transaction_str_representation(self):
        """__str__ should display type, category, and amount."""
        t = make_transaction(self.user, amount="1500.00", t_type="income", category="salary")
        self.assertEqual(str(t), "Income - Salary - ₹1500.00")

    def test_create_saves_to_database(self):
        """Created transaction must persist in the database."""
        make_transaction(self.user, amount="500.00", t_type="expense", category="food")
        self.assertEqual(Transaction.objects.count(), 1)

    def test_create_with_zero_amount_raises_validation_error(self):
        """Zero amount is invalid — model validator should reject it."""
        form = TransactionForm(data={
            "amount": "0",
            "type": "income",
            "category": "salary",
            "date": date.today().isoformat(),
        })
        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)

    def test_create_with_negative_amount_rejected_by_form(self):
        """Negative amount should fail form validation."""
        form = TransactionForm(data={
            "amount": "-500",
            "type": "income",
            "category": "salary",
            "date": date.today().isoformat(),
        })
        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)
        self.assertIn("positive", form.errors["amount"][0].lower())

    def test_create_missing_amount_fails(self):
        """Missing required field 'amount' → form invalid."""
        form = TransactionForm(data={
            "type": "income",
            "category": "salary",
            "date": date.today().isoformat(),
        })
        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)

    def test_create_missing_type_fails(self):
        """Missing required field 'type' → form invalid."""
        form = TransactionForm(data={
            "amount": "100",
            "category": "salary",
            "date": date.today().isoformat(),
        })
        self.assertFalse(form.is_valid())
        self.assertIn("type", form.errors)

    def test_create_invalid_type_string_fails(self):
        """Random string in 'type' should fail choice validation."""
        form = TransactionForm(data={
            "amount": "100",
            "type": "random_gibberish",
            "category": "salary",
            "date": date.today().isoformat(),
        })
        self.assertFalse(form.is_valid())
        self.assertIn("type", form.errors)

    # -------------------------------------------------------------------
    # READ
    # -------------------------------------------------------------------

    def test_list_shows_all_transactions(self):
        """When records exist all of them should be queryable."""
        make_transaction(self.user, amount="100")
        make_transaction(self.user, amount="200")
        self.assertEqual(Transaction.objects.count(), 2)

    def test_empty_queryset_when_no_records(self):
        """When no records exist, queryset is empty (no crash)."""
        qs = Transaction.objects.all()
        self.assertEqual(qs.count(), 0)

    def test_transaction_ordering_latest_first(self):
        """Transactions should be returned latest-date-first."""
        make_transaction(self.user, amount="100", dt=date(2026, 1, 1))
        make_transaction(self.user, amount="200", dt=date(2026, 3, 1))
        first = Transaction.objects.first()
        self.assertEqual(first.amount, Decimal("200"))

    # -------------------------------------------------------------------
    # UPDATE
    # -------------------------------------------------------------------

    def test_update_transaction_saves_changes(self):
        """Valid update should persist new values."""
        t = make_transaction(self.user, amount="1000.00")
        t.amount = Decimal("1500.00")
        t.save()
        t.refresh_from_db()
        self.assertEqual(t.amount, Decimal("1500.00"))

    def test_update_with_negative_amount_rejected(self):
        """Updating with negative amount via form should fail."""
        t = make_transaction(self.user, amount="1000.00")
        form = TransactionForm(
            data={
                "amount": "-100",
                "type": t.type,
                "category": t.category,
                "date": t.date.isoformat(),
            },
            instance=t,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)

    # -------------------------------------------------------------------
    # DELETE
    # -------------------------------------------------------------------

    def test_delete_existing_record(self):
        """Deleting a record removes it from DB."""
        t = make_transaction(self.user)
        pk = t.pk
        t.delete()
        self.assertFalse(Transaction.objects.filter(pk=pk).exists())

    def test_delete_count_decreases(self):
        """Count should decrease by 1 after deletion."""
        make_transaction(self.user)
        make_transaction(self.user)
        t = Transaction.objects.first()
        t.delete()
        self.assertEqual(Transaction.objects.count(), 1)


# ===========================================================================
# 2. FILTERING LOGIC
# ===========================================================================

class FilteringTest(TestCase):
    """Tests for filtering transactions by type, date range, and category."""

    def setUp(self):
        self.user = make_user("filteruser")
        today = date.today()

        # Within last 7 days
        Transaction.objects.create(
            user=self.user, amount=Decimal("1000"), type="income",
            category="salary", date=today - timedelta(days=2),
        )
        Transaction.objects.create(
            user=self.user, amount=Decimal("500"), type="expense",
            category="food", date=today - timedelta(days=4),
        )
        # Older entry — outside 7-day window
        Transaction.objects.create(
            user=self.user, amount=Decimal("300"), type="expense",
            category="travel", date=today - timedelta(days=30),
        )

    def _qs(self):
        return Transaction.objects.all()

    # Filter by type
    def test_filter_income_only(self):
        result = filter_transactions(self._qs(), {"type": "income"})
        self.assertTrue(all(t.type == "income" for t in result))
        self.assertEqual(result.count(), 1)

    def test_filter_expense_only(self):
        result = filter_transactions(self._qs(), {"type": "expense"})
        self.assertTrue(all(t.type == "expense" for t in result))
        self.assertEqual(result.count(), 2)

    # Filter by date range
    def test_filter_last_7_days(self):
        today = date.today()
        result = filter_transactions(self._qs(), {
            "date_from": today - timedelta(days=7),
            "date_to": today,
        })
        self.assertEqual(result.count(), 2)  # only income + food expense

    def test_filter_invalid_date_range_returns_empty(self):
        """start > end should produce an empty queryset gracefully."""
        today = date.today()
        result = filter_transactions(self._qs(), {
            "date_from": today,
            "date_to": today - timedelta(days=7),
        })
        self.assertEqual(result.count(), 0)

    # Filter by category
    def test_filter_by_category_food(self):
        result = filter_transactions(self._qs(), {"category": "food"})
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().category, "food")

    def test_filter_by_category_not_present(self):
        """Category with no matching records should return empty queryset."""
        result = filter_transactions(self._qs(), {"category": "healthcare"})
        self.assertEqual(result.count(), 0)

    def test_filter_combined_type_and_category(self):
        """Combining type=expense and category=travel should narrow results."""
        result = filter_transactions(self._qs(), {
            "type": "expense",
            "category": "travel",
        })
        self.assertEqual(result.count(), 1)

    def test_filter_no_filters_returns_all(self):
        """No filters applied → full queryset returned."""
        result = filter_transactions(self._qs(), {})
        self.assertEqual(result.count(), 3)


# ===========================================================================
# 3. SUMMARY & ANALYTICS SERVICES
# ===========================================================================

class AnalyticsServicesTest(TestCase):
    """Tests for all analytics helper functions in services.py."""

    def setUp(self):
        self.user = make_user("analyticsuser")
        Transaction.objects.create(
            user=self.user, amount=Decimal("3000"), type="income",
            category="salary", date=date(2026, 1, 10),
        )
        Transaction.objects.create(
            user=self.user, amount=Decimal("2000"), type="income",
            category="freelance", date=date(2026, 2, 5),
        )
        Transaction.objects.create(
            user=self.user, amount=Decimal("1000"), type="expense",
            category="food", date=date(2026, 1, 15),
        )
        Transaction.objects.create(
            user=self.user, amount=Decimal("2000"), type="expense",
            category="travel", date=date(2026, 2, 20),
        )

    def test_total_income(self):
        """Sum of all income records → 3000 + 2000 = 5000."""
        self.assertEqual(get_total_income(), Decimal("5000"))

    def test_total_expenses(self):
        """Sum of all expense records → 1000 + 2000 = 3000."""
        self.assertEqual(get_total_expenses(), Decimal("3000"))

    def test_balance_income_minus_expenses(self):
        """Balance = income(5000) – expenses(3000) = 2000."""
        self.assertEqual(get_balance(), Decimal("2000"))

    def test_category_breakdown_has_expenses_and_income(self):
        """Breakdown dict must contain both 'expenses' and 'income' keys."""
        breakdown = get_category_breakdown()
        self.assertIn("expenses", breakdown)
        self.assertIn("income", breakdown)
        self.assertTrue(len(breakdown["expenses"]) > 0)
        self.assertTrue(len(breakdown["income"]) > 0)

    def test_category_breakdown_sums(self):
        """Food total in expense breakdown should equal 1000."""
        breakdown = get_category_breakdown()
        food_entry = next(
            (e for e in breakdown["expenses"] if e["category"] == "Food & Dining"), None
        )
        self.assertIsNotNone(food_entry)
        self.assertEqual(food_entry["total"], Decimal("1000"))

    def test_monthly_summary_groups_by_month(self):
        """Monthly summary should return 2 distinct month entries."""
        summary = get_monthly_summary()
        self.assertEqual(len(summary), 2)

    def test_monthly_summary_net_calculation(self):
        """January net = 3000 income − 1000 expense = 2000."""
        summary = get_monthly_summary()
        # Summary is ordered -month, so January (2026-01) is last
        jan = next((m for m in summary if m["month"].month == 1), None)
        self.assertIsNotNone(jan)
        self.assertEqual(jan["income"], Decimal("3000"))
        self.assertEqual(jan["expenses"], Decimal("1000"))
        self.assertEqual(jan["net"], Decimal("2000"))

    def test_recent_transactions_limit(self):
        """get_recent_transactions(limit=2) should return exactly 2 records."""
        recent = get_recent_transactions(limit=2)
        self.assertEqual(len(recent), 2)

    def test_recent_transactions_ordered_latest_first(self):
        """The first recent transaction should be the latest by date."""
        recent = list(get_recent_transactions(limit=4))
        dates = [t.date for t in recent]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_transaction_count(self):
        """Count should match the total number of transactions in DB."""
        self.assertEqual(get_transaction_count(), 4)


# ===========================================================================
# 4. USER ROLES
# ===========================================================================

class UserRoleAccessTest(TestCase):
    """Tests for Viewer / Analyst / Admin role restrictions."""

    def setUp(self):
        self.client = Client()
        self.viewer  = make_user("viewer_u",  role="Viewer")
        self.analyst = make_user("analyst_u", role="Analyst")
        self.admin   = make_user("admin_u",   role="Admin")
        self.transaction = make_transaction(self.admin)

    # ---- Viewer ----

    def test_viewer_can_access_dashboard(self):
        self.client.login(username="viewer_u", password="pass1234")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_viewer_can_access_transaction_list(self):
        self.client.login(username="viewer_u", password="pass1234")
        response = self.client.get(reverse("transaction_list"))
        self.assertEqual(response.status_code, 200)

    def test_viewer_cannot_create_transaction(self):
        """Viewer POSTing to create should be denied (403)."""
        self.client.login(username="viewer_u", password="pass1234")
        response = self.client.post(reverse("transaction_create"), {
            "amount": "500",
            "type": "income",
            "category": "salary",
            "date": date.today().isoformat(),
        })
        self.assertEqual(response.status_code, 403)

    def test_viewer_cannot_delete_transaction(self):
        self.client.login(username="viewer_u", password="pass1234")
        response = self.client.post(
            reverse("transaction_delete", args=[self.transaction.pk])
        )
        self.assertEqual(response.status_code, 403)
        # Record must still exist
        self.assertTrue(Transaction.objects.filter(pk=self.transaction.pk).exists())

    def test_viewer_cannot_edit_transaction(self):
        self.client.login(username="viewer_u", password="pass1234")
        response = self.client.get(
            reverse("transaction_update", args=[self.transaction.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_viewer_cannot_export_csv(self):
        self.client.login(username="viewer_u", password="pass1234")
        response = self.client.get(reverse("export_csv"))
        self.assertEqual(response.status_code, 403)

    # ---- Analyst ----

    def test_analyst_can_access_dashboard(self):
        self.client.login(username="analyst_u", password="pass1234")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_analyst_can_access_transaction_list(self):
        self.client.login(username="analyst_u", password="pass1234")
        response = self.client.get(reverse("transaction_list"))
        self.assertEqual(response.status_code, 200)

    def test_analyst_can_export_csv(self):
        self.client.login(username="analyst_u", password="pass1234")
        response = self.client.get(reverse("export_csv"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")

    def test_analyst_cannot_delete_transaction(self):
        self.client.login(username="analyst_u", password="pass1234")
        response = self.client.post(
            reverse("transaction_delete", args=[self.transaction.pk])
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Transaction.objects.filter(pk=self.transaction.pk).exists())

    def test_analyst_cannot_create_transaction(self):
        self.client.login(username="analyst_u", password="pass1234")
        response = self.client.get(reverse("transaction_create"))
        self.assertEqual(response.status_code, 403)

    # ---- Admin ----

    def test_admin_can_access_dashboard(self):
        self.client.login(username="admin_u", password="pass1234")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_create_form(self):
        self.client.login(username="admin_u", password="pass1234")
        response = self.client.get(reverse("transaction_create"))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_create_transaction(self):
        self.client.login(username="admin_u", password="pass1234")
        self.client.post(reverse("transaction_create"), {
            "amount": "750.00",
            "type": "expense",
            "category": "food",
            "date": date.today().isoformat(),
            "description": "Admin test",
        })
        # transaction count includes setUp's + this new one
        self.assertTrue(Transaction.objects.filter(description="Admin test").exists())

    def test_admin_can_update_transaction(self):
        self.client.login(username="admin_u", password="pass1234")
        response = self.client.post(
            reverse("transaction_update", args=[self.transaction.pk]),
            {
                "amount": "9999.00",
                "type": self.transaction.type,
                "category": self.transaction.category,
                "date": self.transaction.date.isoformat(),
                "description": "Updated",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.amount, Decimal("9999.00"))

    def test_admin_can_delete_transaction(self):
        self.client.login(username="admin_u", password="pass1234")
        pk = self.transaction.pk
        self.client.post(reverse("transaction_delete", args=[pk]))
        self.assertFalse(Transaction.objects.filter(pk=pk).exists())

    def test_admin_can_export_csv(self):
        self.client.login(username="admin_u", password="pass1234")
        response = self.client.get(reverse("export_csv"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")


# ===========================================================================
# 5. AUTHENTICATION
# ===========================================================================

class AuthenticationTest(TestCase):
    """Tests for login, logout, and access control for unauthenticated users."""

    def setUp(self):
        self.client = Client()
        self.user = make_user("authuser", role="Viewer")

    def test_valid_login_succeeds(self):
        """Correct credentials → 302 redirect (logged in successfully)."""
        response = self.client.post(reverse("login"), {
            "username": "authuser",
            "password": "pass1234",
        })
        self.assertEqual(response.status_code, 302)

    def test_invalid_username_rejected(self):
        """Wrong username → login page re-rendered (200)."""
        response = self.client.post(reverse("login"), {
            "username": "nobody",
            "password": "wrongpass",
        })
        self.assertEqual(response.status_code, 200)

    def test_invalid_password_rejected(self):
        """Correct username, wrong password → login failure."""
        response = self.client.post(reverse("login"), {
            "username": "authuser",
            "password": "incorrectpass",
        })
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_dashboard_redirects_to_login(self):
        """Unauthenticated access to dashboard → redirect to login."""
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])

    def test_unauthenticated_transaction_list_redirects(self):
        response = self.client.get(reverse("transaction_list"))
        self.assertEqual(response.status_code, 302)

    def test_unauthenticated_create_redirects(self):
        response = self.client.get(reverse("transaction_create"))
        self.assertEqual(response.status_code, 302)

    def test_authenticated_user_can_access_dashboard(self):
        self.client.login(username="authuser", password="pass1234")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_already_authenticated_register_redirects_to_dashboard(self):
        """User already logged in visiting /register/ → redirect to dashboard."""
        self.client.login(username="authuser", password="pass1234")
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 302)


# ===========================================================================
# 6. FORM VALIDATION & ERROR HANDLING
# ===========================================================================

class FormValidationTest(TestCase):
    """Tests for form-level validation and meaningful error messages."""

    def test_empty_form_is_invalid(self):
        """Submitting a blank TransactionForm → invalid with errors."""
        form = TransactionForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)
        self.assertIn("type", form.errors)
        self.assertIn("date", form.errors)

    def test_invalid_type_string_rejected(self):
        """A random string in 'type' should not be accepted."""
        form = TransactionForm(data={
            "amount": "100",
            "type": "random_string",
            "category": "salary",
            "date": date.today().isoformat(),
        })
        self.assertFalse(form.is_valid())
        self.assertIn("type", form.errors)

    def test_very_large_amount_accepted(self):
        """Very large amounts (below max_digits limit) should be valid."""
        form = TransactionForm(data={
            "amount": "9999999999.99",   # 12 digits total → within max_digits=12
            "type": "income",
            "category": "salary",
            "date": date.today().isoformat(),
        })
        self.assertTrue(form.is_valid(), msg=form.errors)

    def test_zero_amount_rejected(self):
        """0.00 amount → not positive → form invalid."""
        form = TransactionForm(data={
            "amount": "0.00",
            "type": "income",
            "category": "salary",
            "date": date.today().isoformat(),
        })
        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)

    def test_missing_date_rejected(self):
        """Date is required."""
        form = TransactionForm(data={
            "amount": "100",
            "type": "income",
            "category": "salary",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("date", form.errors)

    def test_description_is_optional(self):
        """Leaving description blank should still produce a valid form."""
        form = TransactionForm(data={
            "amount": "100",
            "type": "income",
            "category": "salary",
            "date": date.today().isoformat(),
            "description": "",
        })
        self.assertTrue(form.is_valid(), msg=form.errors)


# ===========================================================================
# 7. DATABASE BEHAVIOUR
# ===========================================================================

class DatabaseBehaviourTest(TestCase):
    """Tests for data persistence and deletion consistency."""

    def setUp(self):
        self.user = make_user("dbuser")

    def test_data_persists_after_creation(self):
        """Transaction created and then fetched should have same values."""
        t = make_transaction(self.user, amount="2500.00", t_type="income")
        fetched = Transaction.objects.get(pk=t.pk)
        self.assertEqual(fetched.amount, Decimal("2500.00"))
        self.assertEqual(fetched.type, "income")

    def test_deleted_record_does_not_appear(self):
        """After deletion, the record must not be retrievable."""
        t = make_transaction(self.user)
        pk = t.pk
        t.delete()
        with self.assertRaises(Transaction.DoesNotExist):
            Transaction.objects.get(pk=pk)

    def test_multiple_records_persist_independently(self):
        """Deleting one record must not affect others."""
        t1 = make_transaction(self.user, amount="100")
        t2 = make_transaction(self.user, amount="200")
        t1.delete()
        self.assertFalse(Transaction.objects.filter(pk=t1.pk).exists())
        self.assertTrue(Transaction.objects.filter(pk=t2.pk).exists())

    def test_update_persists_to_db(self):
        """Updated value should be available on a fresh fetch from DB."""
        t = make_transaction(self.user, amount="100")
        t.amount = Decimal("999")
        t.save()
        fresh = Transaction.objects.get(pk=t.pk)
        self.assertEqual(fresh.amount, Decimal("999"))


# ===========================================================================
# 8. UI / PAGE FLOW (View-level redirect and response tests)
# ===========================================================================

class PageFlowTest(TestCase):
    """Tests for correct HTTP responses, redirects, and page rendering."""

    def setUp(self):
        self.client = Client()
        self.admin = make_user("flow_admin", role="Admin")
        self.transaction = make_transaction(self.admin)

    def test_create_transaction_redirects_to_list(self):
        """After a successful POST to create, user is sent to transaction_list."""
        self.client.login(username="flow_admin", password="pass1234")
        response = self.client.post(reverse("transaction_create"), {
            "amount": "250.00",
            "type": "expense",
            "category": "food",
            "date": date.today().isoformat(),
            "description": "Flow test redirect",
        })
        self.assertRedirects(response, reverse("transaction_list"))

    def test_delete_redirects_to_list(self):
        """After successful DELETE, view redirects to transaction_list."""
        self.client.login(username="flow_admin", password="pass1234")
        response = self.client.post(
            reverse("transaction_delete", args=[self.transaction.pk])
        )
        self.assertRedirects(response, reverse("transaction_list"))

    def test_delete_nonexistent_id_returns_404(self):
        """Attempting to delete an ID that doesn't exist should return 404."""
        self.client.login(username="flow_admin", password="pass1234")
        response = self.client.post(reverse("transaction_delete", args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_update_nonexistent_id_returns_404(self):
        """Attempting to edit an ID that doesn't exist should return 404."""
        self.client.login(username="flow_admin", password="pass1234")
        response = self.client.get(reverse("transaction_update", args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_invalid_create_data_rerenders_form(self):
        """Invalid POST to create → form page re-rendered (200), no redirect."""
        self.client.login(username="flow_admin", password="pass1234")
        response = self.client.post(reverse("transaction_create"), {
            "amount": "-1",        # invalid
            "type": "income",
            "category": "salary",
            "date": date.today().isoformat(),
        })
        self.assertEqual(response.status_code, 200)

    def test_dashboard_renders_200(self):
        self.client.login(username="flow_admin", password="pass1234")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_transaction_list_renders_200(self):
        self.client.login(username="flow_admin", password="pass1234")
        response = self.client.get(reverse("transaction_list"))
        self.assertEqual(response.status_code, 200)


# ===========================================================================
# 9. EDGE CASES (Interview-level bonus)
# ===========================================================================

class EdgeCaseTest(TestCase):
    """Edge cases: zero transactions, only expenses, same-date entries, large dataset."""

    def setUp(self):
        self.user = make_user("edge_user")

    # --- Zero transactions ---

    def test_total_income_zero_transactions(self):
        """No transactions → income = 0 (no crash)."""
        self.assertEqual(get_total_income(), Decimal("0.00"))

    def test_total_expenses_zero_transactions(self):
        """No transactions → expenses = 0 (no crash)."""
        self.assertEqual(get_total_expenses(), Decimal("0.00"))

    def test_balance_zero_transactions(self):
        """No transactions → balance = 0 (no crash)."""
        self.assertEqual(get_balance(), Decimal("0.00"))

    def test_category_breakdown_empty(self):
        """No transactions → breakdown lists should be empty, not crash."""
        breakdown = get_category_breakdown()
        self.assertEqual(breakdown["expenses"], [])
        self.assertEqual(breakdown["income"], [])

    def test_monthly_summary_empty(self):
        """No transactions → monthly summary should be empty list."""
        summary = get_monthly_summary()
        self.assertEqual(summary, [])

    def test_transaction_count_zero(self):
        self.assertEqual(get_transaction_count(), 0)

    def test_dashboard_view_no_transactions(self):
        """Dashboard should render with 200 even when DB is empty."""
        client = Client()
        client.login(username="edge_user", password="pass1234")
        response = client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

    # --- Only expenses, no income ---

    def test_balance_only_expenses_is_negative(self):
        """When only expenses exist, balance must be negative."""
        make_transaction(self.user, amount="1500", t_type="expense", category="rent")
        make_transaction(self.user, amount="500",  t_type="expense", category="food")
        balance = get_balance()
        self.assertEqual(balance, Decimal("-2000"))

    def test_income_zero_when_only_expenses(self):
        make_transaction(self.user, amount="100", t_type="expense", category="food")
        self.assertEqual(get_total_income(), Decimal("0.00"))

    # --- Same date, multiple entries ---

    def test_same_date_multiple_entries_all_counted(self):
        """Multiple transactions on the same date should all be counted."""
        today = date.today()
        make_transaction(self.user, amount="100", dt=today)
        make_transaction(self.user, amount="200", dt=today)
        make_transaction(self.user, amount="300", dt=today, t_type="expense", category="food")
        self.assertEqual(Transaction.objects.count(), 3)

    def test_same_date_income_sum_correct(self):
        today = date.today()
        make_transaction(self.user, amount="1000", dt=today)
        make_transaction(self.user, amount="2000", dt=today)
        self.assertEqual(get_total_income(), Decimal("3000"))

    # --- Large dataset ---

    def test_large_dataset_loads_without_error(self):
        """1000 records should not cause crashes or timeouts in core functions."""
        transactions = [
            Transaction(
                user=self.user,
                amount=Decimal("100"),
                type="income" if i % 2 == 0 else "expense",
                category="salary" if i % 2 == 0 else "food",
                date=date(2026, 1, 1) + timedelta(days=i % 365),
                description=f"Record {i}",
            )
            for i in range(1000)
        ]
        Transaction.objects.bulk_create(transactions)
        self.assertEqual(Transaction.objects.count(), 1000)

    def test_large_dataset_income_calculated_correctly(self):
        """500 income records × ₹100 = ₹50,000."""
        transactions = [
            Transaction(
                user=self.user,
                amount=Decimal("100"),
                type="income" if i % 2 == 0 else "expense",
                category="salary" if i % 2 == 0 else "food",
                date=date(2026, 1, 1),
            )
            for i in range(1000)
        ]
        Transaction.objects.bulk_create(transactions)
        self.assertEqual(get_total_income(), Decimal("50000"))

    def test_large_dataset_recent_transactions_still_limited(self):
        """get_recent_transactions(limit=5) with 1000 records returns only 5."""
        transactions = [
            Transaction(
                user=self.user,
                amount=Decimal("50"),
                type="expense",
                category="food",
                date=date(2026, 1, 1) + timedelta(days=i % 365),
            )
            for i in range(1000)
        ]
        Transaction.objects.bulk_create(transactions)
        recent = get_recent_transactions(limit=5)
        self.assertEqual(len(recent), 5)
