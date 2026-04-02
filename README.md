**Features**

Add, edit, and delete transactions (income & expenses)
Dashboard showing total income, expenses, and balance
Role-based access:
Viewer → can only view data
Analyst → can filter, search, and export CSV
Admin → full access (CRUD operations)
Filter transactions by date, category, and type
Search transactions by description
Export data as CSV
Pagination (10 records per page)
Basic form validation (amount > 0, required fields)
Responsive UI (works on mobile & desktop)

**Tech Stack**
Backend: Django (Python)
Database: SQLite
Frontend: HTML, CSS (Django Templates)
Authentication: Django Auth + Groups

**Setup**
Install Django
pip install django
Run migrations
python manage.py makemigrations
python manage.py migrate
Create admin user
python manage.py createsuperuser
Run server
python manage.py runserver

Open: http://127.0.0.1:8000/

**Roles Setup**

Go to /admin/ and create groups:

Viewer
Analyst
Admin

Assign users accordingly.

**Pages**
/ → Dashboard
/transactions/ → View transactions
/transactions/add/ → Add (Admin only)
/transactions/export/ → Export CSV
/login/ → Login
/register/ → Register
