# GearGuard - The Ultimate Maintenance Tracker

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com)
[![Turso](https://img.shields.io/badge/Database-Turso-purple.svg)](https://turso.tech)

A comprehensive equipment maintenance management system with role-based access control, work order management, and real-time analytics.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [API Endpoints](#api-endpoints)
- [Database Schema](#database-schema)
- [Authentication](#authentication)
- [Role-Based Access Control](#role-based-access-control)
- [Contributing](#-contributing)
- [Team](#team)

---

## Features

- **Equipment Management** - Track assets with specifications, health scores, and QR codes
- **Work Order Management** - Create, assign, and track maintenance work orders
- **Preventive Maintenance** - Schedule recurring tasks with automatic work order generation
- **Parts Inventory** - Manage spare parts with low stock alerts
- **Team Management** - Organize technicians into teams with role assignments
- **Reports & Analytics** - Dashboard with KPIs, health reports, and cost analysis
- **Security** - JWT authentication with role-based access control

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend Framework | FastAPI (Python 3.11+) |
| Database | Turso (LibSQL) |
| Authentication | JWT (python-jose) |
| Password Hashing | bcrypt (passlib) |
| Validation | Pydantic v2 |

---

## Project Structure

```
GearGuard/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Configuration
│   │   ├── database.py          # Turso connection
│   │   ├── api/v1/              # API endpoints
│   │   └── core/                # Security & permissions
│   ├── migrations/              # Database schema
│   ├── .env.example             # Environment template
│   └── requirements.txt         # Dependencies
├── DB_Flow.jpeg
└── README.md
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Turso account (https://turso.tech)

### Installation

```bash
# Clone and checkout branch
git clone https://github.com/Ansh-Chamriya/GG.git
cd GG
git checkout basic_database

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\activate      # Windows
source .venv/bin/activate     # Linux/Mac

# Install dependencies
cd backend
pip install -r requirements.txt

# Configure environment
copy .env.example .env        # Windows
cp .env.example .env          # Linux/Mac
# Edit .env with your Turso credentials

# Run server
uvicorn app.main:app --reload --port 8000
```

### Access

- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

---

## API Endpoints

| Group | Prefix | Description |
|-------|--------|-------------|
| Auth | `/api/v1/auth` | Registration, login, tokens |
| Users | `/api/v1/users` | User management |
| Equipment | `/api/v1/equipment` | Asset management |
| Work Orders | `/api/v1/workorders` | Work order lifecycle |
| Schedules | `/api/v1/schedules` | Preventive maintenance |
| Parts | `/api/v1/parts` | Inventory management |
| Reports | `/api/v1/reports` | Analytics & dashboards |

See full documentation at `/docs` when server is running.

---

## Database Schema

27 tables organized into domains:

| Domain | Tables |
|--------|--------|
| Auth & Users | users, roles, permissions, sessions |
| Organization | organizations, locations, teams |
| Equipment | equipment, equipment_categories, meter_readings |
| Maintenance | maintenance_schedules, checklist_templates |
| Work Orders | work_orders, work_order_tasks, work_order_comments |
| Inventory | parts_inventory, parts_usage |
| Logging | audit_logs, notifications |

---

## Authentication

JWT-based authentication with access and refresh tokens.

```
POST /api/v1/auth/register    # Create account
POST /api/v1/auth/login       # Get tokens
POST /api/v1/auth/refresh     # Refresh access token
POST /api/v1/auth/logout      # Invalidate session
```

Include token in requests:
```
Authorization: Bearer <access_token>
```

---

## Role-Based Access Control

| Role | Level | Access |
|------|-------|--------|
| super_admin | 1 | Full system access |
| admin | 2 | Organization admin |
| manager | 3 | Equipment & work orders |
| technician | 4 | Perform maintenance, report issues |

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## Team

| Name | Role |
|------|------|
| Ansh Chamriya | Developer |

---

## 📝 Notes

- This project is developed as part of a Hackathon
- See `backend/ARCHITECTURE.md` for detailed technical documentation
- See `backend/TEAM_REFERENCE.md` for quick reference guide

---

## Resources

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Turso Docs](https://docs.turso.tech/)
- [Pydantic Docs](https://docs.pydantic.dev/)
