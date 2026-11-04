Chalane ka tareeka (laptop/Termux):
1. pip install -r requirements.txt
2. PostgreSQL banao, phir: psql "$DATABASE_URL" -f schema.sql
3. export DATABASE_URL=... SECRET_KEY=...
4. python app.py  ->  http://localhost:5000

Render: Build = pip install -r requirements.txt
        Start = gunicorn app:app
        Env vars: DATABASE_URL (Render PostgreSQL ka Internal URL), SECRET_KEY

Photo upload (Cloudinary): cloudinary.com pe free account banao, Dashboard se
"API environment variable" copy karo aur Render me CLOUDINARY_URL naam se daalo.
Database me sab SQL files order se chalao: schema.sql, schema_round2..5.sql
