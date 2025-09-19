React test client for the Lambda crawler

Prereqs: Node.js (16+ recommended) and npm/yarn

Run dev server (uses port 3000):

1. cd react-client
2. create a file named `.env` with:

VITE_API_URL="https://{api-id}.execute-api.{region}.amazonaws.com/Prod/crawl"

3. Install and start:

npm install
npm run dev

Open http://localhost:3000 and test the form.

Notes:

- The app reads `VITE_API_URL` at build/dev time. For local dev place it in `.env`.
- Make sure your deployed API has CORS allowing `http://localhost:3000` (it does per `template.yaml` change).

If you edited `package.json`, run `npm install` again to fetch the `@vitejs/plugin-react` dependency.
