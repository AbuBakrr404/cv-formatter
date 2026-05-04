# Railway Deployment Guide

This guide walks you through deploying the CV Formatter to Railway so your team can access it via a URL instead of installing Python on each computer.

## What you'll end up with

- A URL like `cv-formatter-production-abc123.up.railway.app`
- Anyone with the URL + the team password can use it
- The app runs 24/7 — no need to start it locally
- Your Anthropic API key is set ONCE on Railway, not by each user

---

## Before you start

You need:
- ✅ A Railway account (you have one)
- ✅ A GitHub account (free at github.com — needed to upload your code)
- ✅ Your Anthropic API key (the `sk-ant-api03-...` you've been using)
- ✅ A team password you'll choose now (something memorable like `ProTalent2026!`)

Roughly 20 minutes total.

---

## Part 1 — Upload the project to GitHub

Railway pulls your code from GitHub, so the project needs to live there first.

### Step 1: Create a new GitHub repository

1. Go to **[github.com/new](https://github.com/new)**
2. **Repository name:** `cv-formatter` (or anything you like)
3. **Visibility:** select **Private** (this is your business code — keep it private)
4. **Don't** tick "Initialize this repository with..."
5. Click **"Create repository"**
6. On the next page, you'll see commands — keep this tab open, you'll need the URL

### Step 2: Install Git (if you don't have it)

1. Go to **[git-scm.com/download/win](https://git-scm.com/download/win)**
2. Download and run the installer
3. Click "Next" through everything (default settings are fine)
4. Verify by opening a new command prompt and typing: `git --version`

### Step 3: Upload your project

Open a command prompt in your `cv_automation` folder (address bar → type `cmd` → Enter), then run these commands one at a time:

```
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/cv-formatter.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username. Use the URL from Step 1 if different.

When it asks for credentials, GitHub will pop up a sign-in window — just sign in with your GitHub account.

When done, refresh your GitHub repo page — you should see all your files there.

---

## Part 2 — Deploy to Railway

### Step 1: Create a new Railway project

1. Go to **[railway.app](https://railway.app)** and sign in
2. Click **"New Project"** (top right)
3. Click **"Deploy from GitHub repo"**
4. If prompted, authorize Railway to access your GitHub
5. Find your `cv-formatter` repo in the list and click it
6. Railway starts building automatically

### Step 2: Set environment variables

This is where you securely give Railway your API key and team password.

1. In your Railway project, click on your service (the box that appeared)
2. Click the **"Variables"** tab at the top
3. Click **"New Variable"** and add these one at a time:

**Variable 1:**
- Name: `ANTHROPIC_API_KEY`
- Value: paste your `sk-ant-api03-...` key

**Variable 2:**
- Name: `APP_PASSWORD`
- Value: the team password you chose (e.g. `ProTalent2026!`)

4. Click **"Add"** after each one. Railway will automatically redeploy.

### Step 3: Generate a public URL

By default, Railway services aren't publicly accessible — you need to expose them:

1. Click the **"Settings"** tab
2. Scroll to **"Networking"** section
3. Click **"Generate Domain"**
4. Railway gives you a URL like `cv-formatter-production-abc123.up.railway.app`
5. Click the URL to test it — you should see the password screen

### Step 4: Wait for deployment to finish

In the **"Deployments"** tab, you'll see the build status. The first build takes 3-5 minutes (installing Python, dependencies, etc.). When you see ✅ "Active", you're live.

---

## Part 3 — Test it works

1. Open the Railway URL in a browser
2. You should see a password screen titled "🔒 Pro Talent CV Formatter"
3. Enter your team password
4. Upload a test CV (the `sample_data/sample_cv.docx` from the project)
5. Click **"Process CVs"** and verify it works end-to-end

---

## Part 4 — Share with the team

Send this to your team via WhatsApp or email:

> **CV Formatter — now online**
>
> URL: `<your Railway URL>`
> Password: `<your team password>`
>
> Just visit the URL, sign in once with the password, and start uploading CVs.
> Bookmark it for daily use. The full instruction guide is attached.
>
> If you forget the password or have any issues, contact <your name>.

Attach the `CV_Automation_Team_Guide.docx` file from earlier so they have the usage instructions.

---

## Updating the app later

When you want to make changes (e.g. tweak the AI prompts, update the template):

1. Make changes locally on your computer
2. Open command prompt in the project folder
3. Run:
   ```
   git add .
   git commit -m "Description of what you changed"
   git push
   ```
4. Railway automatically detects the push and redeploys (takes 2-3 minutes)
5. The team's URL stays the same — no action needed on their side

---

## Cost monitoring

### Anthropic costs
Check at **console.anthropic.com → Usage**. Each CV costs about R0.06-R0.15. Set up a usage alert at $10 to get notified before bills get out of hand.

### Railway costs
Check at **railway.app → Project → Usage**. For a small Streamlit app like this, expect ~$5-10/month. Railway gives you $5 free credit on signup.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| "Application failed to respond" on Railway URL | Check the **Deployments** tab in Railway — look for red errors in the build log. Most common: typo in environment variable name. |
| Password screen appears but rejects correct password | Check `APP_PASSWORD` variable in Railway — make sure there are no extra spaces or quotes. |
| "Server configuration error: ANTHROPIC_API_KEY is not set" | The `ANTHROPIC_API_KEY` variable wasn't added correctly. Re-add it in Railway → Variables. |
| Push to GitHub fails | Run `git pull --rebase` first, then try `git push` again. |
| Build takes more than 10 minutes | Cancel and retry — Railway sometimes hits transient build issues. |

---

## Security notes

- The team password and API key are stored as **encrypted environment variables** on Railway — never visible in the URL, never committed to GitHub
- The `.gitignore` file prevents accidentally uploading the `.env` file (which would expose your key)
- If anyone leaves the team, **change the password in Railway**:
  1. Go to Variables tab
  2. Edit `APP_PASSWORD` to a new value
  3. Railway redeploys automatically
  4. Send the new password to your remaining team members

- If your API key is ever leaked, **rotate it immediately**:
  1. Go to console.anthropic.com → API Keys
  2. Delete the old key
  3. Create a new one
  4. Update `ANTHROPIC_API_KEY` in Railway Variables
