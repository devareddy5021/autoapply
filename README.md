# autoapply

**JobAutoApply** is an intelligent, transparent job application tracking and external dispatch copilot built with Django, PostgreSQL/SQLite, and PySpark/pypdf.

---

## 🌟 Key Features

- **Multi-Source Job Discovery**: Seamless tracking and integration across LinkedIn, Wellfound (AngelList), Indeed, Naukri, and direct company career portals.
- **External Application Dispatcher**: Automatic compilation of candidate dossiers (resume, custom pitch notes, authorization, notice period) and external application handoff.
- **Transparent Match Engine**: Real-time compatibility scoring across target role, skills, location, work-mode preference, and compensation fit.
- **Resume Hub**: PDF resume uploading and automated text extraction.
- **Full Application Pipeline**: Track stages from *Saved*, *Ready*, *Review Required*, to *Submitted*, *Interview*, and *Offers*.

---

## 🚀 Getting Started

### 1. Setup Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` and adjust database credentials as needed:
```bash
cp .env.example .env
```

### 3. Run Migrations & Seed Demo Data
```bash
python manage.py migrate
python manage.py seed_demo_data
python manage.py seed_demo_user
```
Demo credentials:
- **Username**: `demo`
- **Password**: `Password123!`

### 4. Run Development Server
```bash
python manage.py runserver
```
Navigate to `http://127.0.0.1:8000` in your browser.

---

## 🧪 Running Tests
```bash
python manage.py test
```
