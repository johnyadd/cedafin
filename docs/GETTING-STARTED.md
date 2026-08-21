# Getting started — VS Code on Windows

From an empty folder to a running vertical slice: Next.js talking to Supabase and to the Python engine, with the schema applied and the golden tests green.

**This guide assumes you already ship finanyst.com** — Next.js on Vercel, Supabase, a Python FastAPI engine on Render, PowerShell in VS Code. It skips what that already proves you have and concentrates on the genuinely new parts. There are only three:

| New here | Why it's new |
|---|---|
| **Supabase CLI, tracked migrations** | Finanyst has no `supabase/` folder — migrations are run in the dashboard, untracked. Here the DB *is* the asset, so schema lives in git and gets pushed from the command line. |
| **A staging Supabase project** | Finanyst doesn't need one. Here a bad migration against append-only history destroys data you cannot re-fetch. |
| **Local Python + pytest** | The Finanyst engine lives on Render. This one you'll run and test locally every day, so the venv has to work on your machine — a recurring friction point. |

Budget about 90 minutes. Work in order — every step verifies before the next depends on it.

**Before you start:** put all downloaded files in your `Downloads` folder. The scripts install them from there.

---

## Step 0 — Two checks, not a full setup

Node, npm, git, VS Code, the execution policy and the Tailwind/ESLint/PowerShell extensions are all already working — Finanyst proves it. Skip them.

Only two things genuinely need checking:

```powershell
node -v          # must be 20+; Finanyst may be on an older major
py --version     # must be 3.11+ AND working locally, not just on Render
```

**If `node -v` reports 25 or 26**, you are on the Current line rather than LTS. Node cuts even majors in April and odd ones in October, and each goes Active LTS the following October — so v26 (April 2026) becomes LTS around October 2026. It will work, but pin the version explicitly in Step 1 so local and Vercel cannot silently diverge, and treat it as the first suspect if `npm install` fails on a native build.

**If `py` fails or is under 3.11**, install from python.org with **Add Python to PATH** ticked. The Finanyst engine runs on Render, so a broken local Python may never have surfaced — here you run it every day.

**Docker is not required.** This setup links to hosted Supabase projects rather than running one locally, so `supabase start` never enters the picture.

Two extensions you probably don't have yet, for inspecting the database from inside the editor:

```powershell
code --install-extension mtxr.sqltools
code --install-extension mtxr.sqltools-driver-pg
```

And, if Pylance isn't already installed from earlier Python work:

```powershell
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
```

---

## Step 1 — Scaffold

```powershell
New-Item -ItemType Directory -Force -Path C:\Projects | Out-Null
Set-Location C:\Projects
powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\bootstrap.ps1"
```

This creates `C:\Projects\cediwise`, installs dependencies, creates the folder tree, sets up the Python venv, installs the supplied files, and makes the first commit.

Then open it:

```powershell
Set-Location C:\Projects\cediwise
code .
```

**Pin the Node version** so your machine and Vercel's build runtime cannot drift apart — a build that passes locally and fails in CI reads as a deploy problem when it is really a version problem:

```powershell
node -e "const f='package.json',p=require('./'+f);p.engines={node:'>=22 <27'};require('fs').writeFileSync(f,JSON.stringify(p,null,2)+'\n')"
Set-Content -Path .nvmrc -Value "26" -NoNewline
```

Adjust `.nvmrc` to whatever `node -v` reported. In Step 10, set Vercel's **Node.js Version** to the highest option at or below it.

**Verify:** `lib/scoring/config.ts`, `lib/compliance/licence-status.ts`, `supabase/migrations/*_core_schema.sql` and `docs/ARCHITECTURE.md` all exist, and `package.json` now carries an `engines` field.

---

## Step 2 — Install the remaining code files

Still in `C:\Projects\cediwise`:

```powershell
$dl = Join-Path $env:USERPROFILE "Downloads"
New-Item -ItemType Directory -Force -Path .\engine\tests | Out-Null
Copy-Item (Join-Path $dl "engine-main.py")         .\engine\main.py -Force
Copy-Item (Join-Path $dl "engine-metrics.py")      .\engine\metrics.py -Force
Copy-Item (Join-Path $dl "engine-test-metrics.py") .\engine\tests\test_metrics.py -Force
Copy-Item (Join-Path $dl "lib-env.ts")             .\lib\env.ts -Force
Copy-Item (Join-Path $dl "lib-supabase.ts")        .\lib\supabase.ts -Force
```

**Verify:**

```powershell
Get-ChildItem .\engine, .\lib -Recurse -File | Select-Object FullName
```

---

## Step 3 — Create the Supabase project

In the browser, at supabase.com:

1. **New project**, name it `cediwise-prod`.
2. **Region** — see §8 of ARCHITECTURE.md. Ghana's Data Protection Act may bear on where personal data is hosted; if you're storing only emails, EU (Frankfurt) is a reasonable default, but confirm before you hold anything more.
3. Save the **database password** in your password manager immediately. It is shown once.
4. Create a second project, `cediwise-staging`. Not optional — §15.1 explains why: a bad migration against append-only history destroys data you cannot re-fetch, because provider factsheets get replaced and the old ones are gone.

From **Settings → API**, collect: Project URL, `anon` key, `service_role` key. From **Settings → General**: the project reference.

---

## Step 4 — Fill in `.env.local`

Open `.env.local` in VS Code and paste each value **on the same line as its `=`**.

> This is the single most repeated error on the Finanyst build: a key wrapped onto the following line parses as empty, every call fails, and the error surfaces three layers away from the cause.

Generate the token secret:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Set `PYTHON_ENGINE_URL=http://localhost:8000` and `COMPLIANCE_PHASE=1`.

**Verify without printing any secret:**

```powershell
Get-Content .env.local | ForEach-Object { if ($_ -match "^([A-Z_]+)=(.*)$") { "{0,-32} {1}" -f $Matches[1], $(if ($Matches[2].Trim()) { "set (" + $Matches[2].Trim().Length + " chars)" } else { "MISSING" }) } }
```

Never paste the output of a plain `Get-Content .env.local` anywhere. Three API keys leaked that way on the previous project.

---

## Step 5 — Apply the schema  ⚠ new territory

**This is the step that differs most from how you work today.** On Finanyst there is no `supabase/` folder and migrations are pasted into the dashboard SQL editor, untracked. Here the schema lives in git and is pushed from the command line, so it is reviewable, replayable and recoverable.

```powershell
npx supabase login
npx supabase link --project-ref <your-staging-ref>
npx supabase db push
```

`login` opens a browser for an access token. `link` asks for the database password from Step 3 — the one shown once.

Do **staging first**, always. Once it's clean, repeat `link` and `db push` against the production ref.

From here on, **never edit schema in the dashboard.** Every change is a new file in `supabase/migrations/`:

```powershell
npx supabase migration new add_whatever
```

Edit the generated file, push to staging, then production. The dashboard SQL editor is for queries and seeds only. This is the discipline Finanyst never had, and it is the single practice most worth carrying forward.

Then load the crawl plan. In the Supabase dashboard → **SQL Editor**, paste the contents of `supabase/seed_source_targets.sql` and run it.

**Verify:**

```powershell
npx supabase db diff --linked
```

An empty diff means the database matches your migration. Then in the SQL Editor:

```sql
select label, url, parser, cadence_days from source_targets order by label;
```

You should see the SEC register pages and the benchmark sources.

---

## Step 6 — Run the engine

```powershell
Set-Location .\engine
.\.venv\Scripts\Activate.ps1
pip install fastapi uvicorn pydantic pytest
python -m pytest tests -q
```

**If activation fails** — a recurring friction on this setup — the venv is usually missing or was built by a different interpreter. Rebuild it:

```powershell
Remove-Item -Recurse -Force .\.venv -ErrorAction SilentlyContinue
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install fastapi uvicorn pydantic pytest
```

Confirm you are inside it before installing anything — the prompt should read `(.venv)` and:

```powershell
(Get-Command python).Source
```

should point inside `engine\.venv`, not at your system Python. Then tell VS Code: **Ctrl+Shift+P → Python: Select Interpreter →** the `.venv` entry, or Pylance will resolve imports against the wrong environment and red-underline working code.

**Expect 13 passed.** These are the golden tests, and they are the foundation of the whole numeric layer — a change that moves one of these numbers is a methodology change, not a bug fix (§15.3).

Start the service:

```powershell
uvicorn main:app --reload --port 8000
```

**Verify** in a second PowerShell window:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Expect `status: ok` and an engine version.

Leave this terminal running. In VS Code use **Terminal → Split Terminal** so you have the engine in one pane and Next.js in the other.

---

## Step 7 — Run the app

In the second pane, back at the project root:

```powershell
npm run dev
```

Open http://localhost:3000.

If it starts, `lib/env.ts` has validated every variable. If a variable is missing or malformed, the app **refuses to boot** with a message naming the exact variable — that is the file working as intended, not a failure.

---

## Step 8 — Prove the vertical slice end to end

Create `app/api/dev-check/route.ts` in VS Code and paste:

```ts
import { NextResponse } from "next/server";
import { checkEngine } from "@/lib/env";
import { publicClient } from "@/lib/supabase";

export async function GET() {
  const engine = await checkEngine();
  const { count, error } = await publicClient()
    .from("products")
    .select("*", { count: "exact", head: true });
  return NextResponse.json({
    engine,
    database: error ? { ok: false, detail: error.message } : { ok: true, products: count ?? 0 },
  });
}
```

**Verify:**

```powershell
Invoke-RestMethod http://localhost:3000/api/dev-check | ConvertTo-Json -Depth 4
```

Both `ok: true`, with `products: 0`. That is Next.js → Supabase → engine all wired. Delete this route once Phase 1 has a real `/admin/health` page.

---

## Step 9 — Commit and push

```powershell
git add -A
git commit -m "Engine, env validation, Supabase clients, schema applied"
gh repo create cediwise --private --source=. --push
```

If you don't use the GitHub CLI, create the repo in the browser, then:

```powershell
git remote add origin https://github.com/<you>/cediwise.git
git branch -M main
git push -u origin main
```

---

## Step 10 — Deploy

Same shape as finmodels-engine and finanyst.com, so this is familiar ground.

**Engine → Render.** New Web Service, root directory `engine`, build `pip install -r requirements.txt`, start `uvicorn main:app --host 0.0.0.0 --port $PORT`. Starter tier for the same no-cold-start reason as finmodels-engine. One thing that service doesn't have: set `ALLOWED_ORIGIN` to your Vercel domain, since this engine enforces CORS.

**App → Vercel.** Import, add every `.env.local` variable under Settings → Environment Variables, point `PYTHON_ENGINE_URL` at the Render URL, redeploy.

Check **Settings → General → Node.js Version** matches your `.nvmrc`. If your local major isn't offered yet — likely on a Current-line release — pick the highest available and know you are running ahead locally. That gap is fine day to day and is exactly what the `engines` range exists to bound.

Env values live in exactly two places, as on Finanyst: `.env.local` and the Vercel dashboard — plus Render for the engine's own two. Render needs no Anthropic key here; extraction runs in Next.js.

**Verify:** hit `/api/dev-check` on the deployed domain. Both `ok: true`.

---

## Daily workflow

Two terminal panes, always:

```powershell
# pane 1 — engine
Set-Location C:\Projects\cediwise\engine ; .\.venv\Scripts\Activate.ps1 ; uvicorn main:app --reload --port 8000

# pane 2 — app
Set-Location C:\Projects\cediwise ; npm run dev
```

Before every commit:

```powershell
npx tsc --noEmit          # baseline is ZERO, not "stable"
npm run lint
Set-Location .\engine ; python -m pytest tests -q ; Set-Location ..
```

A TypeScript error count of **1** usually means a fatal parse error, not near-success — `tsc` abandons the project and stops counting.

### Editing files from PowerShell

Two hard-won rules from the Finanyst build:

- **Multi-line `.Replace()` never matches.** Working files use CRLF, so any pattern containing a bare `` `n `` silently fails to match — no error, nothing flagged. Use `[System.IO.File]::ReadAllLines()`, loop the array applying single-line `-replace`, then `WriteAllLines`.
- **Long here-strings silently write nothing.** Above roughly 80 lines the file simply doesn't appear. Use a `List[string]` with `$o.Add()` per line, split across two blocks, written with `WriteAllLines`.

Then verify the edit itself — a successful `git push` proves nothing about a file that had no changes to stage.

---

## What comes next

You now have the machinery and no data. That is the correct order, and the next step is **not** more code.

Go to ARCHITECTURE.md §17.9 and do the week-one sequence: scrape the licensee register, pick ten fund managers, record their price and factsheet URLs, pull three SEC annual reports, and **time one full manual refresh cycle**. That number multiplied by 52 is the honest annual cost of this business, and it is the Phase 0 exit test.

Build the ingestion pipeline only once you know what you are ingesting.
