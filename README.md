# Mazashields — Backend

REST API Mazashi Livestock Distribution System, dibangun dengan **Django REST Framework** dan di-deploy di **Railway**.

🌐 **Live API:** https://mazashield-backend-production.up.railway.app  
🔗 **Frontend:** https://mazashield-frontend.vercel.app

---


## Tim Pengembang

**Kelompok AdalahPokoknya** — Client: PT Mazashi Semuda Farm

| Nama | NPM |
|------|-----|
| Alfian Bassam Firjatullah | 2306212695 |
| Mawla Raditya Pambudi | 2306275323 |
| Regina Meilani Aruan | 2306275632 |
| Rosanne Valerie | 2306222986 |
| Sezza Auraghaniya Winanda | 2306207291 |

---

## Struktur Direktori

```
mazashield-backend/
├── config/                 # Konfigurasi proyek Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/                   # Aplikasi Django
│   ├── accounts/           # Manajemen user & autentikasi
│   ├── mazdafarm/          # Katalog hewan ternak
│   ├── mazdaging/          # Katalog daging
│   ├── investernak/        # Katalog investasi ternak
│   ├── pesanan/            # Manajemen pesanan
│   ├── pembayaran/         # Verifikasi pembayaran
│   └── laporan/            # Laporan penjualan & investasi
├── .env.example            # Template environment variables
├── requirements.txt
├── manage.py
└── Procfile                # Konfigurasi Railway
```

---

## Prasyarat

- Python 3.10+
- pip

---

## Instalasi & Menjalankan Lokal

```bash
# 1. Clone repo
git clone <url-repo-backend>
cd mazashield-backend

# 2. Buat dan aktifkan virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Konfigurasi environment variables
cp .env.example .env
```

Isi `.env`:

```env
SECRET_KEY=your-django-secret-key
DEBUG=True
DATABASE_URL=postgresql://user:password@host/dbname
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

```bash
# 5. Jalankan migrasi
python manage.py migrate

# 6. (Opsional) Buat superuser
python manage.py createsuperuser

# 7. Jalankan dev server
python manage.py runserver
```

API tersedia di: **http://localhost:8000**  
Django Admin: **http://localhost:8000/admin**

---

## Branching Strategy

| Branch | Fungsi |
|--------|--------|
| `main` | Production |
| `staging` | Pre-production |
| `development` | Integrasi fitur |
| `feat/<nama>` | Branch individu |

Alur: `feat/<nama>` → `development` → `staging` → `main`

---

## Deployment

Deploy otomatis ke Railway setiap push ke branch `main`. Set environment variables di Railway Dashboard sesuai `.env.example`.