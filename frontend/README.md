# Enterprise Document RAG Frontend

Dependency-free frontend for the existing FastAPI backend.

## Run

Start the backend first:

```powershell
.\venv311\Scripts\python.exe main.py
```

Start the frontend proxy server:

```powershell
node frontend\server.js
```

Open:

```text
http://127.0.0.1:5173
```

The frontend calls the backend through `/api/v1/*`. By default the proxy targets `http://127.0.0.1:9000`.

To use a different backend URL:

```powershell
$env:API_TARGET="http://127.0.0.1:9000"; node frontend\server.js
```
