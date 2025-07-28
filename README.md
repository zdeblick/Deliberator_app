
# FastAPI + Jekyll Starter (for Render)

This is a starter template that connects a **FastAPI backend** (hosted on [Render](https://render.com)) with a **Jekyll frontend** (hosted on GitHub Pages).

---

## 🗂 Structure

```
fastapi-jekyll-render/
├── backend/        # FastAPI app (deployed on Render)
│   ├── main.py
│   ├── requirements.txt
│   └── render.yaml
├── frontend/       # Jekyll site (deployed via GitHub Pages)
│   ├── index.html
│   └── _config.yml
└── README.md
```

---

## 🚀 Backend Setup (Render)

1. Create a GitHub repo and push this code
2. Go to [Render Dashboard](https://dashboard.render.com)
3. Click **“New Web Service”**
4. Select your repo (authorize access if needed)
5. Render will detect `render.yaml` and auto-configure the service
6. Deploy and copy your backend URL (e.g., `https://deliberator-app.onrender.com`)

---

## 🌐 Frontend Setup (GitHub Pages)

1. Go to your GitHub repo settings → **Pages**
2. Set source to `frontend/` folder on the `main` branch
3. GitHub will deploy your Jekyll site at `https://zdeblick.github.io/Deliberator_app`

> NOTE: Edit the URL in `frontend/index.html` to point to your deployed backend.

---

## 📝 Customization

- To change the frontend, edit `frontend/index.html`
- To add FastAPI routes, modify `backend/main.py`
- To deploy changes: `git commit` and `git push` — both Render and GitHub Pages redeploy automatically

---

## 🔒 CORS Warning

This template allows all origins via CORS for development. Consider restricting origins before going to production.
