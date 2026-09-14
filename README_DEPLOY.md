# BhoomiSeva production foundation

This package removes the hard-coded demo accounts and stores real user accounts and complaint requests in a database.

## Local run

1. Create a Python virtual environment.
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and set a strong SECRET_KEY.
4. Set `COOKIE_SECURE=0` for local HTTP testing.
5. Run `python app.py`.

## Production deployment

Use a managed PostgreSQL database and set DATABASE_URL. Deploy the web service with:

`gunicorn app:app`

The included `render.yaml` is a starting point for Render. Create the web service and a PostgreSQL database in your hosting account, then set DATABASE_URL to the database connection string.

## Important

This does NOT invent government land records. Live Telangana land records, survey/GIS boundaries, weather, soil, GPS and document verification require authorized APIs/data sources and their credentials. Those must be connected before those screens can claim to show live government data.
