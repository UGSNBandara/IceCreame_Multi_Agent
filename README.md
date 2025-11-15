# Coffee Shop Agent

A FastAPI-based chatbot for a coffee shop with text-to-speech (TTS) capabilities.

## Features
- Menu browsing and ordering
- Cart management
- Order tracking with status updates
- Offline TTS using pyttsx3
- SQLite database for persistence

## Setup Locally
1. Clone the repo:
   ```bash
   git clone https://github.com/yourusername/your-repo.git
   cd your-repo
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Fill in your `GOOGLE_API_KEY` (from [Google AI Studio](https://aistudio.google.com))

4. Run the app:
   ```bash
   uvicorn api:app --reload
   ```
   - Access at `http://127.0.0.1:8000`
   - API docs at `http://127.0.0.1:8000/docs`

## Deploy to Railway
1. Push your code to GitHub.

2. Go to [Railway.app](https://railway.app) and sign up/login.

3. Click "New Project" > "Deploy from GitHub repo" > Select your repo.

4. Railway auto-detects Python and installs from `requirements.txt`.

5. In Railway dashboard > Variables tab, add:
   - `GOOGLE_API_KEY`: Your Gemini API key
   - `SQLITE_DB_PATH`: `coffee.db` (optional, default)

6. Set start command (if not auto-detected):
   - Go to Settings > Start Command: `uvicorn api:app --host 0.0.0.0 --port $PORT`

7. Deploy! Railway will build and give you a URL (e.g., `https://your-app.railway.app`).

8. On pushes to the connected branch, Railway auto-redeploys.

## API Endpoints
- `GET /health`: Health check
- `POST /agent/`: Chat with the agent
- `POST /menu/items`: Add menu item
- `PUT /menu/items/{id}`: Update menu item
- `DELETE /menu/items/{id}`: Delete menu item
- `GET /orders`: List orders
- `PUT /orders/{id}/status`: Update order status
- `GET /orders/{id}`: Get single order
- `POST /generate-voice/`: Generate TTS audio

## Notes
- TTS uses pyttsx3 (offline, works on Railway).
- Database: SQLite (`coffee.db`), auto-initialized with sample menu.
- Free Railway tier: 512MB RAM, sleeps after inactivity.

## Contributing
- Use branches for features.
- Add tests in `tests/`.