# Deployment notes

Keeping this here so I don't have to re-figure out the whole Render setup again next time I redeploy or start a new project.

## What this project does (quick recap for myself)

Takes a raw sales CSV/Excel file, figures out which column is which (order id, revenue, region, customer info, etc.) even if the headers are named something random, cleans up the data (missing values, wrong types, outliers), and then exposes it through a FastAPI backend with 30+ analytics routes: KPIs, revenue trend, top/lowest products, regional and gender/age breakdowns, repeat customers, sales velocity, product combos, anomaly detection, discount impact, and a bunch more. There's a simple dashboard (`ui.html`) on top that hits all of these.

## What I added on top of the original code, just for deployment

- Moved `ui.html` into a `static/` folder. `main.py`'s homepage route only looks for `static/ui.html` or `static/index.html`, so if it's not sitting there, the live URL just shows a plain JSON status message instead of the actual dashboard.
- `.gitignore` so the sqlite db, `data/`, and `logs/` folders don't get pushed to GitHub. No point pushing 20+ MB of local junk.
- `Procfile` tells Render (or Railway) what command to run to start the app.
- `render.yaml` so Render reads this and auto-fills the setup instead of me typing the build/start commands manually every time.

Didn't have to touch the actual app code for any of this. The frontend already calls the API with a relative path, so it just works on whatever domain it ends up on.

## Step 1: push to GitHub

```
cd deploy_project
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<username>/<repo>.git
git push -u origin main
```

GitHub doesn't run the app, it just stores the code. Render pulls from here.

Note to self: when it asks for a password, it's not my actual GitHub password anymore, it's a personal access token (Settings, then Developer settings, then Personal access tokens, then generate one with "repo" access, paste that in instead).

## Step 2: deploy on Render

Went with Render since it's free and doesn't fight with FastAPI like some other free hosts do.

1. Go to render.com and sign up with GitHub
2. Click New, pick Web Service, connect the repo
3. It should read `render.yaml` automatically. If not:
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Instance: Free
4. Click Create, wait about 2 to 5 min for the first build, then you get the live URL

Things to remember about the free tier:
- It goes to sleep after about 15 min with no traffic, first visit after that takes 30 to 50 sec to wake back up. Not a big deal for showing people the project, just don't expect it to be instant every time.
- The filesystem resets every time it redeploys or restarts, so the sqlite db and any uploaded files don't stick around long term. The app still works fine for live demos (upload, clean and analyze all happen in real time), it just won't remember old sessions across restarts. If I ever want that to persist, `db.py` already reads `DATABASE_URL` from env, so I could just point it at a free Postgres instead, no code change needed.

## Other options I considered

Railway works basically the same way, just doesn't have a proper free tier anymore (small monthly credit only), so Render made more sense.

Skipped PythonAnywhere and a full VPS. PythonAnywhere doesn't play nice with FastAPI (it's built for WSGI apps), and a VPS means I'd have to set up nginx and manage the server myself, which isn't worth it for this.

## Before pushing, sanity check locally

```
pip install -r requirements.txt
uvicorn main:app --reload
```

Go to localhost:8000, it should show the actual dashboard. If it shows JSON instead, `ui.html` isn't sitting in `static/` where it needs to be.
