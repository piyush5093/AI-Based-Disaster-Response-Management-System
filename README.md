# AI-Based Disaster Response Management System

This is a disaster operations command platform designed to integrate real-time disaster event feeds, model disaster impact zones, predict resource demands, and generate optimized allocation and logistics plans for relief agencies.

## Setup Instructions

1. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Copy the example environment file and fill in your details (e.g., MongoDB URI):
   ```bash
   cp .env.example .env
   ```
   Open `.env` and set `MONGO_URI` to your MongoDB Atlas connection string or local MongoDB instance.

4. **Run the Application:**
   ```bash
   uvicorn app.main:app --reload
   ```

## Verification
To verify that the application and database connection are working, visit:
[http://localhost:8000/api/health](http://localhost:8000/api/health)

You should see a response like:
```json
{
  "status": "ok",
  "db": "connected"
}
```
