# 🛡️ GearGuard Backend - Team Quick Reference

## 📊 Database Tables Summary (27 Tables)

| # | Table Name | Purpose | Key Relationships |
|---|------------|---------|-------------------|
| 1 | `roles` | Role definitions (super_admin, admin, manager, etc.) | - |
| 2 | `permissions` | Permission definitions (resource:action format) | - |
| 3 | `role_permissions` | Maps roles to permissions | roles, permissions |
| 4 | `organizations` | Multi-tenant organization data | - |
| 5 | `users` | User accounts and profiles | roles, organizations |
| 6 | `sessions` | Active user sessions for JWT refresh | users |
| 7 | `password_reset_tokens` | Password recovery tokens | users |
| 8 | `locations` | Facility/site hierarchical locations | organizations |
| 9 | `equipment_categories` | Equipment classification | organizations |
| 10 | `equipment` | Main equipment/asset records | orgs, locations, categories |
| 11 | `meter_readings` | Equipment meter tracking | equipment, users |
| 12 | `teams` | Technician team definitions | organizations, users |
| 13 | `team_members` | Team membership | teams, users |
| 14 | `checklist_templates` | Reusable maintenance checklists | organizations |
| 15 | `maintenance_schedules` | Preventive maintenance schedules | equipment, checklists |
| 16 | `work_orders` | Work order management | equipment, schedules, teams |
| 17 | `work_order_tasks` | Task breakdown for work orders | work_orders |
| 18 | `work_order_comments` | Communication on work orders | work_orders, users |
| 19 | `work_order_checklists` | Completed checklist responses | work_orders, templates |
| 20 | `parts_inventory` | Spare parts management | organizations, locations |
| 21 | `parts_usage` | Parts consumption tracking | work_orders, parts |
| 22 | `equipment_parts` | Equipment-part associations | equipment, parts |
| 23 | `maintenance_history` | Equipment maintenance log | equipment, work_orders |
| 24 | `audit_logs` | System audit trail | organizations, users |
| 25 | `notifications` | User notifications | users, organizations |
| 26 | `reports` | Saved report configurations | organizations |
| 27 | `dashboards` | Custom dashboard layouts | organizations, users |

---

## 🔐 Role Hierarchy

```
Level 1: super_admin   → Full system access (all organizations)
Level 2: admin         → Organization admin (manage users, settings)
Level 3: manager       → Manage equipment, work orders, teams
Level 4: technician    → Perform maintenance, report issues, update work orders
```

---

## 🌐 API Endpoints Summary (100+ Endpoints)

### Authentication (10 endpoints)
- `POST /auth/register` - Register new user
- `POST /auth/login` - User login → Returns JWT tokens
- `POST /auth/logout` - User logout
- `POST /auth/refresh` - Refresh access token
- `POST /auth/forgot-password` - Request password reset
- `POST /auth/reset-password` - Reset password
- `GET /auth/verify-email/{token}` - Verify email
- `GET /auth/me` - Get current user
- `PUT /auth/me` - Update profile
- `PUT /auth/me/password` - Change password

### Organizations (6 endpoints)
- CRUD: `POST`, `GET`, `GET/{id}`, `PUT/{id}`, `DELETE/{id}`
- `GET /{id}/stats` - Organization statistics

### Users (8 endpoints)
- CRUD: `POST`, `GET`, `GET/{id}`, `PUT/{id}`, `DELETE/{id}`
- `PUT /{id}/role` - Change user role
- `GET /{id}/workorders` - User's work orders
- `GET /{id}/activity` - User activity log

### Equipment (12 endpoints)
- CRUD: `POST`, `GET`, `GET/{id}`, `PUT/{id}`, `DELETE/{id}`
- `GET /{id}/history` - Maintenance history
- `GET /{id}/workorders` - Related work orders
- `GET /{id}/schedules` - Maintenance schedules
- `GET /{id}/parts` - Associated parts
- `POST /{id}/meter-reading` - Add meter reading
- `GET /{id}/meter-readings` - Get meter readings
- `POST /{id}/report-issue` - Report issue
- `GET /{id}/qr` - Generate QR code

### Work Orders (15 endpoints)
- CRUD: `POST`, `GET`, `GET/{id}`, `PUT/{id}`, `DELETE/{id}`
- `PUT /{id}/status` - Update status
- `PUT /{id}/assign` - Assign work order
- `POST /{id}/start` - Start work
- `POST /{id}/complete` - Complete work
- `POST /{id}/hold` - Put on hold
- `POST /{id}/cancel` - Cancel
- `GET /{id}/tasks` - Get tasks
- `PUT /{id}/tasks/{task_id}` - Update task
- `GET /{id}/comments` + `POST /{id}/comments` - Comments
- `POST /{id}/parts` - Add parts used
- `GET /{id}/checklist` + `PUT /{id}/checklist` - Checklist

### Schedules (8 endpoints)
- CRUD: `POST`, `GET`, `GET/{id}`, `PUT/{id}`, `DELETE/{id}`
- `POST /{id}/generate-workorder` - Create work order
- `GET /upcoming` - Upcoming maintenance
- `GET /overdue` - Overdue maintenance

### Parts/Inventory (10 endpoints)
- CRUD: `POST`, `GET`, `GET/{id}`, `PUT/{id}`, `DELETE/{id}`
- `POST /{id}/adjust-stock` - Adjust stock
- `GET /{id}/usage-history` - Usage history
- `GET /low-stock` - Low stock alerts
- `POST /{id}/equipment` - Link to equipment

### Reports (12 endpoints)
- `GET /dashboard` - Dashboard data
- `GET /equipment-health` - Equipment health
- `GET /workorder-summary` - Work order summary
- `GET /maintenance-costs` - Cost analysis
- `GET /technician-performance` - Performance metrics
- `GET /downtime` - Downtime analysis
- `GET /parts-usage` - Parts usage
- `POST /custom` - Custom report
- `GET /saved` + `POST /saved` - Saved reports
- `GET /export/{format}` - Export (PDF/Excel)

### Others
- **Teams**: 7 endpoints
- **Locations**: 5 endpoints
- **Categories**: 5 endpoints
- **Checklists**: 5 endpoints
- **Notifications**: 5 endpoints
- **Dashboards**: 5 endpoints
- **Audit Logs**: 2 endpoints

---

## 🔑 JWT Token Flow

```
1. User logs in with email/password
2. Server validates credentials
3. Server creates:
   - Access Token (15 min expiry) - contains user_id, org_id, role, permissions
   - Refresh Token (7 days expiry) - stored in sessions table
4. Client stores tokens (httpOnly cookies or secure storage)
5. Client sends Access Token in Authorization header: "Bearer <token>"
6. When Access Token expires, use Refresh Token to get new tokens
7. On logout, invalidate session in database
```

---

## 📁 Project Structure (FastAPI)

```
gearguard-backend/
├── app/
│   ├── main.py           # FastAPI entry point
│   ├── config.py         # Settings from env
│   ├── database.py       # Turso connection
│   ├── api/v1/           # API route handlers
│   ├── core/             # Security, permissions, exceptions
│   ├── models/           # Database models
│   ├── schemas/          # Pydantic request/response models
│   ├── services/         # Business logic layer
│   ├── repositories/     # Database access layer
│   └── utils/            # Helper utilities
├── migrations/           # SQL migration files
├── tests/                # Unit & integration tests
├── .env                  # Environment variables
└── requirements.txt      # Python dependencies
```

---

## 🚀 Getting Started Commands

```bash
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install fastapi uvicorn libsql python-jose[cryptography] passlib[bcrypt] python-multipart pydantic-settings python-dotenv ulid-py qrcode pillow

# 3. Set up environment variables (copy .env.example to .env)

# 4. Run migrations (using Turso CLI or Python script)

# 5. Start development server
uvicorn app.main:app --reload --port 8000

# API Docs available at: http://localhost:8000/docs
```

---

## 📋 Task Division for Team

### Developer 1: Auth & Users
- [ ] Implement `/auth/*` endpoints
- [ ] JWT token generation/validation
- [ ] Password hashing with bcrypt
- [ ] Session management
- [ ] User CRUD operations

### Developer 2: Equipment & Locations
- [ ] Equipment CRUD
- [ ] Categories management
- [ ] Locations management
- [ ] Meter readings
- [ ] QR code generation

### Developer 3: Work Orders & Schedules
- [ ] Work order CRUD
- [ ] Task management
- [ ] Comment system
- [ ] Maintenance schedules
- [ ] Auto work order generation

### Developer 4: Parts & Reports
- [ ] Parts inventory CRUD
- [ ] Stock management
- [ ] Parts usage tracking
- [ ] Dashboard API
- [ ] Report generation

### All Developers
- [ ] Write unit tests
- [ ] API documentation
- [ ] Error handling
- [ ] Permission checks

---

## 🔗 Important Links

- **Turso Docs**: https://docs.turso.tech/sdk/python/quickstart
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **JWT Guide**: https://python-jose.readthedocs.io/
- **Pydantic v2**: https://docs.pydantic.dev/latest/

---

**Created**: December 27, 2024  
**For**: GearGuard Hackathon Team
