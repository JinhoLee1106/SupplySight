
  # SupplySight Dashboard

React + Vite frontend for the SupplySight supply risk monitoring system.

## Requirements

- Node.js 18 or higher
- npm 9 or higher
- The FastAPI backend running on port 8000 (see root `README.md`)

## Running the code

Install dependencies:

```bash
npm install
```

Start the dev server:

```bash
npm run dev
```

Open **http://localhost:3000** in your browser.

The dev server automatically proxies all `/api` requests to `http://127.0.0.1:8000`, so the FastAPI backend must be running first. See the root `README.md` for backend setup instructions.

## Build for production

```bash
npm run build
```

Output goes to `build/`.
  