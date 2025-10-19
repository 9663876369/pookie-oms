# Order Management System (Render-ready)

## Features
- Add orders (customer, item, qty, total, paid)
- Orders list with pending amount and status
- Edit / Delete / Mark Completed
- Printable invoice
- Daily / Monthly reports with per-day summary
- Simple admin login (default: admin / password). You should set environment variables on Render.

## Set environment variables on Render
- `SECRET_KEY` — a secure random string
- `ADMIN_USER` — admin username (default: admin)
- `ADMIN_PASS` — admin password (default: password)
- `BUSINESS_NAME` — name to display on invoice (e.g. Pookie Sells)

## Deploy on Render (Quick steps)
1. Create a new **Web Service** on Render.
2. Connect your GitHub repository (or you can deploy by uploading code).
3. Set the build command: `pip install -r requirements.txt`
4. Set the start command: `gunicorn app:app`
5. Add the environment variables above.
6. Deploy — Render will install dependencies and start the app.

## Run locally
```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=app.py
export SECRET_KEY='your-secret'
python app.py
```

