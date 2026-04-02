# Finance Tracking System

A Django-based web application for tracking personal and business finances. Manage income and expenses, view analytics dashboards, and control access with role-based permissions.

## Features

- **Transaction Management**: Full CRUD operations for income and expense records
- **Dashboard Analytics**: Visual summaries with total income, expenses, balance, category breakdowns, and monthly trends
- **Role-Based Access Control**: Three roles using Django Groups:
  - **Viewer**: Can view transactions and dashboard summaries
  - **Analyst**: Can view, filter, search transactions, view analytics, and export CSV
  - **Admin**: Full access — CRUD operations, manage data, and all analyst capabilities
- **Filtering & Search**: Filter transactions by date range, category, type, and description search
- **Pagination**: Transaction list is paginated (10 per page)
- **CSV Export**: Export all transactions to a downloadable CSV file
- **Form Validation**: Amount must be positive, required fields enforced, with clear error messages
- **Responsive Design**: Dark-themed modern UI that works on desktop and mobile

## Tech Stack

- **Backend**: Python 3.x, Django 5.x
- **Database**: SQLite (default Django DB)
- **Frontend**: Django Templates, Vanilla CSS
- **Auth**: Django's built-in authentication system with Groups for roles

## Project Structure

```
intern_assignment/
├── finance_manager/        # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── tracker/                # Main application
│   ├── models.py           # Transaction model
│   ├── views.py            # All view logic (dashboard, CRUD, auth)
│   ├── forms.py            # Transaction, filter, and registration forms
│   ├── services.py         # Business logic (analytics, computations)
│   ├── decorators.py       # Role-based access control decorators
│   ├── context_processors.py  # Template context (user role)
│   ├── admin.py            # Django admin registration
│   ├── urls.py             # App URL routing
│   ├── tests.py            # Unit tests
│   └── templates/tracker/  # HTML templates
│       ├── base.html
│       ├── dashboard.html
│       ├── transaction_list.html
│       ├── transaction_form.html
│       ├── transaction_confirm_delete.html
│       ├── login.html
│       └── register.html
├── static/css/styles.css   # Application stylesheet
├── manage.py
└── README.md
```

## Setup Instructions

### Prerequisites
- Python 3.10+ installed
- pip (Python package manager)

### 1. Install Django
```bash
pip install django
```

### 2. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Create a Superuser (Admin)
```bash
python manage.py createsuperuser
```

### 4. Set Up Roles (Groups)
After running the server, go to **Django Admin** (`/admin/`) and create three groups:
- `Viewer`
- `Analyst`
- `Admin`

Assign users to appropriate groups. Alternatively, new users who register via the app are automatically assigned the `Viewer` role.

### 5. Run the Server
```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` to access the application.

## How to Run Tests
```bash
python manage.py test tracker
```

## Assumptions Made

1. **Global Transactions**: All transactions are visible to all authenticated users. Role determines what actions a user can perform (view only, filter/export, or full CRUD).
2. **Default Role**: New users registered via the registration page are auto-assigned the `Viewer` role.
3. **Categories**: Categories are predefined as choices in the model (Salary, Freelance, Food, Rent, etc.) rather than a separate model for simplicity.
4. **Currency**: The app displays amounts in INR (₹) — this can be easily changed in templates.
5. **SQLite**: Used as the default database for simplicity. Can be swapped for PostgreSQL or others via Django settings.
6. **No Frontend Framework**: All pages are server-rendered using Django templates with vanilla CSS.

## Pages

| Page | URL | Access |
|------|-----|--------|
| Dashboard | `/` | All authenticated users |
| Transaction List | `/transactions/` | All authenticated users |
| Add Transaction | `/transactions/add/` | Admin only |
| Edit Transaction | `/transactions/<id>/edit/` | Admin only |
| Delete Transaction | `/transactions/<id>/delete/` | Admin only |
| Export CSV | `/transactions/export/` | Analyst, Admin |
| Login | `/login/` | Public |
| Register | `/register/` | Public |
| Django Admin | `/admin/` | Superusers |
