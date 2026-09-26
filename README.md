# NB BEADS STUDIO E-Commerce FastAPI + MongoDB Backend

This is the production-ready backend for the NB BEADS STUDIO E-Commerce application, built using FastAPI, asynchronous MongoDB engine (Motor & Beanie ODM), and server-rendered Jinja2 templates for the admin dashboard.

## Tech Stack
- **Python 3.10+** (FastAPI, Uvicorn, Jinja2 templates)
- **MongoDB Atlas** (Async Motor driver + Beanie Document ODM)
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
4. Create a `.env` file from the variables (or update `.env` directly) with your MongoDB connection:
   ```env
   MONGODB_URI=mongodb+srv://<username>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority
   DATABASE_NAME=jineee
   JWT_SECRET=supersecretjwtkey12345!
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=1440
   PORT=8000
   HOST=0.0.0.0
   CORS_ORIGINS=*
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
- 1 Super Admin (`admin` / `admin123`)
- 5 Product Categories (Jewellery, Couple Things, Macrame, Fashion, Gifts)
- 10 Test Customer Users (`user1@nbbeadsstudio.com` to `user10@...`)
- 5 Hero Promotional Banners
- 20+ Detailed Products across all categories with prices, SKUs, inventory, and images
- Default System Settings (Store name, currency, tax rates, contact info)
