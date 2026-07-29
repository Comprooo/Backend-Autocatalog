# Backend Autocatalog

REST API backend untuk aplikasi **Autocatalog** — platform company profile showroom mobil yang menyediakan katalog kendaraan, sistem penjadwalan test drive, dan AI Assistant berbasis chat.

## Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.11)
- **Database**: MongoDB (via [Motor](https://motor.readthedocs.io/) + [Beanie ODM](https://beanie-odm.dev/))
- **Auth**: JWT (python-jose + bcrypt/passlib)
- **Image Storage**: [Cloudinary](https://cloudinary.com/)
- **AI Chat**: Ollama (self-hosted LLM)
- **Deployment**: Docker + Docker Compose / Vercel (serverless)

## Struktur Direktori

```
Backend-Autocatalog/
├── app/
│   ├── main.py              # Entry point FastAPI
│   ├── core/
│   │   ├── config.py        # Konfigurasi env (pydantic-settings)
│   │   ├── database.py      # Koneksi MongoDB (init & close)
│   │   └── dependencies.py  # Dependency injection (auth guard)
│   ├── models/              # Beanie ODM Documents
│   │   ├── car.py
│   │   ├── user.py
│   │   ├── schedule.py
│   │   ├── location.py
│   │   └── available_slot.py
│   ├── schemas/             # Pydantic request/response schemas
│   ├── repositories/        # Data access layer (CRUD per model)
│   ├── services/            # Business logic layer
│   │   ├── auth_service.py
│   │   ├── car_service.py
│   │   ├── schedule_service.py
│   │   ├── available_slot_service.py
│   │   ├── location_service.py
│   │   └── admin_service.py
│   ├── routes/v1/           # API route handlers
│   │   ├── auth.py
│   │   ├── cars.py
│   │   ├── admin_cars.py
│   │   ├── schedules.py
│   │   ├── admin_schedules.py
│   │   ├── admin_stats.py
│   │   ├── available_slots.py
│   │   ├── locations.py
│   │   ├── upload.py
│   │   └── ai.py
│   ├── ai/
│   │   └── chat.py          # AI chat service (Ollama)
│   └── static/
│       └── chat.html        # UI debug AI chat
├── seed/                    # Script seeder database
├── api/
│   └── index.py             # Entry point Vercel (serverless)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## API Endpoints

Semua endpoint diawali dengan prefix `/api/v1`.

### Auth (`/auth`)
| Method | Path | Deskripsi | Auth |
|--------|------|-----------|------|
| POST | `/auth/register` | Registrasi user baru | — |
| POST | `/auth/login` | Login & dapatkan JWT token | — |
| POST | `/auth/logout` | Logout (client-side token deletion) | ✓ |
| GET | `/auth/me` | Ambil data user yang sedang login | ✓ |
| PUT | `/auth/me` | Update profil user | ✓ |
| POST | `/auth/change-password` | Ganti password | ✓ |

### Katalog Mobil (`/cars`)
| Method | Path | Deskripsi | Auth |
|--------|------|-----------|------|
| GET | `/cars` | List semua mobil (filter, pagination) | — |
| GET | `/cars/{car_id}` | Detail satu mobil | — |

### Admin — Mobil (`/admin/cars`)
| Method | Path | Deskripsi | Auth |
|--------|------|-----------|------|
| POST | `/admin/cars` | Tambah mobil baru | Admin |
| PUT | `/admin/cars/{car_id}` | Update data mobil | Admin |
| PATCH | `/admin/cars/{car_id}/status` | Update status mobil | Admin |
| DELETE | `/admin/cars/{car_id}` | Hapus mobil | Admin |

### Penjadwalan Test Drive (`/schedules`)
| Method | Path | Deskripsi | Auth |
|--------|------|-----------|------|
| POST | `/schedules` | Buat jadwal baru | Customer |
| GET | `/schedules/me` | Lihat jadwal milik saya | Customer |
| GET | `/schedules/{id}` | Detail jadwal | Customer |
| PATCH | `/schedules/{id}/cancel` | Batalkan jadwal | Customer |
| PATCH | `/schedules/{id}/reschedule` | Reschedule jadwal | Customer |

### Admin — Jadwal (`/admin/schedules`)
| Method | Path | Deskripsi | Auth |
|--------|------|-----------|------|
| GET | `/admin/schedules` | Semua jadwal (pagination) | Admin |
| GET | `/admin/schedules/{id}` | Detail jadwal | Admin |
| PATCH | `/admin/schedules/{id}/status` | Update status jadwal | Admin |
| PATCH | `/admin/schedules/{id}/reject` | Tolak jadwal | Admin |
| DELETE | `/admin/schedules/{id}` | Hapus jadwal | Admin |

### Lokasi & Slot Tersedia
| Method | Path | Deskripsi | Auth |
|--------|------|-----------|------|
| GET | `/locations` | List semua lokasi | — |
| POST | `/admin/locations` | Tambah lokasi | Admin |
| GET | `/available-slots` | List slot waktu tersedia | — |
| POST | `/admin/available-slots` | Tambah slot waktu | Admin |

### AI Chat
| Method | Path | Deskripsi | Auth |
|--------|------|-----------|------|
| POST | `/chat` | Chat dengan AI Assistant | ✓ |
| GET | `/ai/inventory-search` | Pencarian inventori (internal) | Internal Token |

### Upload & Lainnya
| Method | Path | Deskripsi | Auth |
|--------|------|-----------|------|
| POST | `/upload/image` | Upload gambar ke Cloudinary | Admin |
| GET | `/admin/stats` | Statistik dashboard admin | Admin |
| GET | `/health` | Health check | — |

## Cara Menjalankan

### 1. Menggunakan Docker Compose (Rekomendasi)

```bash
# Salin konfigurasi environment
cp .env.example .env
# Edit .env sesuai kebutuhan

# Jalankan semua service
docker compose up --build

# Seed database (opsional)
docker compose run seed
```

Service yang berjalan:
- **API**: `http://localhost:8000`
- **MongoDB**: `localhost:27017`
- **Ollama** (AI): `localhost:11434`

### 2. Menjalankan Secara Lokal

```bash
# Buat virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Salin dan isi file .env
cp .env.example .env

# Jalankan server development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Environment Variables

Salin `.env.example` menjadi `.env` lalu isi nilai berikut:

| Variable | Keterangan |
|----------|------------|
| `MONGODB_URL` | Connection string MongoDB |
| `MONGODB_DB_NAME` | Nama database MongoDB |
| `JWT_SECRET_KEY` | Secret key untuk signing JWT |
| `INTERNAL_SERVICE_TOKEN` | Token autentikasi internal AI service |
| `CLOUDINARY_CLOUD_NAME` | Nama cloud Cloudinary |
| `CLOUDINARY_API_KEY` | API Key Cloudinary |
| `CLOUDINARY_API_SECRET` | API Secret Cloudinary |
| `UPLOAD_DIR` | Direktori penyimpanan file upload lokal |
| `BASE_URL` | Base URL aplikasi |

## Dokumentasi API

Setelah server berjalan, akses dokumentasi interaktif di:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Roles Pengguna

| Role | Keterangan |
|------|------------|
| `customer` | Pengguna biasa, bisa browsing katalog & booking test drive |
| `admin` | Akses penuh ke manajemen katalog, jadwal, dan statistik |
| `internal_ai_service` | Digunakan oleh AI service untuk query inventori |