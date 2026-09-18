# NB BEADS STUDIO E-Commerce FastAPI + PostgreSQL Backend

This is the production-ready backend for the NB BEADS STUDIO E-Commerce application, built using FastAPI, asynchronous PostgreSQL engine (`asyncpg` & SQLAlchemy), and server-rendered Jinja2 templates for the admin dashboard.

## Tech Stack
- **Python 3.10+** (FastAPI, Uvicorn, Jinja2 templates)
- **PostgreSQL 18** (Async PostgreSQL engine with `asyncpg` and JSONB support)
- **Security**: JWT authentication, Bcrypt password hashing, XSS/CSRF protections, rate limiting
- **Logging**: Rotating files (`logs/access.log`, `logs/errors.log`)
- **Pillow**: Automatic image resizing and thumbnail generation

---

## Installation & Setup

1. Clone or copy the directory and navigate to the backend folder:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file from the variables (or update `.env` directly) with your PostgreSQL connection:
   ```env
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=nbbeadsstudio
   DB_USER=postgres
   DB_PASSWORD=<your_postgres_password>
   JWT_SECRET=supersecretjwtkey12345!
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=1440
   ```

---

## Running the Application

### Local Development
To run the server locally with auto-reload:
```bash
uvicorn app:app --reload
```
- **API Docs**: `http://localhost:8000/docs` or `http://localhost:8000/redoc`
- **Admin Panel**: `http://localhost:8000/admin/login`

### Admin Login Credentials
- **Username**: `admin`
- **Password**: `admin123`

---

## Auto-Seeding Database
On the first run (or if the database collection is empty), the application automatically seeds:
- **1 Admin Account**
- **5 Categories** (Jewellery, Couple Things, Macrame, Fashion, Gifts)
- **20+ Products** (populated with product slugs, stock levels, MRPs, sale prices, and tags)
- **10 Customers**
- **5 Homepage/Offer Banners**

---

## Docker Support
You can run the application containerized alongside a MongoDB instance.

1. Start container services:
   ```bash
   docker-compose up --build
   ```
2. The server will be accessible at `http://localhost:8000`.

---

## Logging & Security
- Access requests are logged in `logs/access.log`.
- Server errors and tracebacks are logged in `logs/errors.log`.
- All APIs implement unified JSON response formatting.
