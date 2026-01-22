# offo-backend
backend source code of OFFO


Backend Setup (Local – Windows)

Follow these steps to run the backend locally on your machine.

1️⃣ Get the code from GitHub
Option A: Download ZIP

Go to the GitHub repository

Click Code → Download ZIP

Extract it to your local folder

Option B: Clone using Git (recommended)

git clone https://github.com/VSW-Data-Solutions/offo-backend.git
cd offo-backend

2️⃣ Navigate to backend folder
cd backend

3️⃣ Create & activate virtual environment (Windows)
Create venv (if not already created)
python -m venv venv

Activate venv
venv\Scripts\activate


You should see (venv) in your terminal.

4️⃣ Install dependencies
pip install -r requirements.txt

5️⃣ Configure environment variables

Open the .env file in the backend folder and update:

DATABASE_URL=postgresql://username:password@localhost:5432/ofo_db


🔹 Replace:

username → your PostgreSQL username

password → your PostgreSQL password

6️⃣ Create database manually (PostgreSQL)

Login to PostgreSQL:

psql -U username


Create database:

CREATE DATABASE ofo_db;


Exit:

\q

7️⃣ Run database migrations (Alembic)

This will create/update all tables and columns automatically:

alembic upgrade head


✅ If this succeeds, your database schema is ready.

8️⃣ Start the backend server

Run FastAPI using Uvicorn:

uvicorn app.main:app --reload


You should see:

Uvicorn running on http://127.0.0.1:8000

9️⃣ Verify backend is running

Open in browser:

http://localhost:8000/docs


Swagger UI should load successfully ✅