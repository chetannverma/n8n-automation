# Step-by-Step Submission Guide
## n8n Workflow: Raw Content → Branded PDF
### Subject: Economic and Social Issues | Chapter: Economic Growth and Development

---

## What You Are Submitting

| File | Purpose |
|---|---|
| `generate_pdf.py` | Python script that converts raw notes into a styled, branded PDF |
| `n8n_workflow.json` | n8n workflow that automates the full pipeline |

---

## Files & Folder Setup

Create this folder structure on your machine (or n8n server):

```
economic-notes/
├── generate_pdf.py          ← the Python script
├── n8n_workflow.json        ← the n8n workflow
├── Untitled.png             ← Types of Economic Growth diagram
├── Untitled_1.png           ← Traditional Approach cards
├── Untitled_2.png           ← (other diagrams from project)
├── ...                      ← all other PNG images
├── Screenshot_20231211_153014.png
└── Screenshot_20231211_114429.png
```

**Important:** The folder path in `n8n_workflow.json` must be updated to your actual path.
Open `n8n_workflow.json`, find the node called **"Set Configuration"**, and update:

```js
workDir: '/data/workflows/economic-notes',   // ← change this to your actual path
```

---

## Step 1 — Install Python Dependencies

Open a terminal and run:

```bash
pip install reportlab pillow requests
```

These three libraries power the PDF generation.

---

## Step 2 — Test the Python Script Locally

```bash
python3 generate_pdf.py --img-dir /path/to/economic-notes --output output.pdf
```

You should see:
```
[INFO] Fetching logo images …
[INFO] Building PDF → output.pdf
[INFO] Done ✓  (XXXX KB)
```

Open `output.pdf` to verify it looks correct:
- Blue header with logo (left) + subject/chapter text (right)
- Green accent line below header
- Watermark logo centred at 20% opacity
- Branded blue section headings
- Green callout boxes for key points
- Comparison tables with blue headers
- All images embedded
- Blue footer with phone, website, and page number

---

## Step 3 — Import the Workflow into n8n

1. Open your n8n instance in the browser (default: `http://localhost:5678`)
2. Click **"Workflows"** in the left sidebar
3. Click **"Import from File"** (top-right button)
4. Select `n8n_workflow.json`
5. The workflow will appear with all nodes connected

---

## Step 4 — Update the Work Directory in n8n

1. In the imported workflow, click the **"Set Configuration"** node
2. Find this line in the JavaScript code:
   ```js
   workDir: '/data/workflows/economic-notes',
   ```
3. Change it to the **absolute path** of your folder, e.g.:
   - Linux/Mac: `/home/yourname/economic-notes`
   - Windows (WSL): `/mnt/c/Users/yourname/economic-notes`
4. Click **Save**

---

## Step 5 — Enable the Execute Command Node

The **"Run generate_pdf.py"** node uses n8n's `Execute Command` node, which runs shell commands.

> **If you see a warning** that Execute Command is disabled:
> 1. Open your n8n config file (usually `.env` or `docker-compose.yml`)
> 2. Add: `N8N_RESTRICT_FILE_ACCESS_TO=` (leave blank to allow all paths)
> 3. And: `EXECUTIONS_PROCESS=main`
> 4. Restart n8n

---

## Step 6 — Run the Workflow

1. Click the **"Manual Trigger"** node (the play button ▶)
2. Click **"Execute Workflow"**
3. Watch the nodes turn green one by one:
   - Manual Trigger → Set Configuration
   - Fetch Header Logo + Fetch Watermark Logo (run in parallel)
   - Merge Logo Fetches → Prepare Python Command
   - Run generate_pdf.py → Check Result → Success?
   - → Success Summary (green path)

4. The final **"Success Summary"** node will output:
   ```json
   {
     "status": "SUCCESS",
     "pdf": "/path/to/Economic_Growth_and_Development.pdf",
     "subject": "Economic and Social Issues",
     "chapter": "Economic Growth and Development",
     "generatedAt": "2026-01-01T10:00:00.000Z"
   }
   ```

---

## Step 7 — Verify the Output PDF

Open the generated PDF and check:

| Element | Expected |
|---|---|
| Header (left) | Full Anuj Jindal logo |
| Header (right) | "Economic and Social Issues / Economic Growth and Development" |
| Header colour | Blue (#1B71AC) |
| Accent line | Green (#2AB573) |
| Watermark | Logo centred, 20% opacity |
| Section bars | Blue background, white text |
| Callout boxes | Green border, light green background |
| Tables | Blue header row, alternating white/light-blue rows |
| Footer | Blue bar, phone + website + page number |

---

## Workflow Node Summary

```
[Manual Trigger]
      │
[Set Configuration]  ← brand colours, URLs, paths
      │
  ┌───┴───┐
  ↓       ↓
[Fetch   [Fetch
Header   Watermark
Logo]    Logo]
  └───┬───┘
      ↓
[Merge Logo Fetches]
      │
[Prepare Python Command]  ← builds the shell command string
      │
[Run generate_pdf.py]     ← Execute Command node
      │
[Check Result]            ← validates exit code
      │
[Success?]  ── YES → [Success Summary]
            └─ NO  → [Error Handler]
```

---

## Customisation Notes

| What to change | Where |
|---|---|
| Output filename | `Set Configuration` node → `outputFilename` |
| Subject / Chapter text | `Set Configuration` node → `subject` / `chapter` |
| Brand colours | `generate_pdf.py` → `BLUE` / `GREEN` constants (top of file) |
| Add more images | Add them to your `workDir`, then add `Image(...)` calls in `_build_story()` |
| Add email delivery | Add an **Email** or **Gmail** node after **Success Summary** |
| Upload to Google Drive | Add a **Google Drive** node after **Success Summary** |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: reportlab` | Run `pip install reportlab pillow requests` |
| `[WARN] Could not fetch logo URL` | Check internet connectivity; logos are fetched at runtime |
| PDF has no images | Verify PNG files are in the same folder as `generate_pdf.py` (or use `--img-dir`) |
| n8n Execute Command blocked | Set `N8N_RESTRICT_FILE_ACCESS_TO=` in your n8n `.env` |
| `exitCode !== 0` in Check Result | Check the stderr output in the Run node for the Python traceback |

---
