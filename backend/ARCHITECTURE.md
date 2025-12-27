# 🛡️ GearGuard - Backend Architecture Document

## 📋 Table of Contents
1. [System Overview](#system-overview)
2. [Database Schema (Turso/LibSQL)](#database-schema)
3. [Role-Based Access Control (RBAC)](#rbac)
4. [API Endpoints](#api-endpoints)
5. [Authentication Flow](#authentication-flow)
6. [FastAPI Project Structure](#project-structure)
7. [Implementation Guide](#implementation-guide)

---

## 🎯 System Overview

**GearGuard** is an ultimate maintenance tracker that allows organizations to:
- Track equipment and machinery maintenance schedules
- Manage work orders and technicians
- Monitor equipment health and history
- Generate reports and analytics
- Control access based on user roles

### Technology Stack
- **Backend Framework**: FastAPI (Python)
- **Database**: Turso (LibSQL - SQLite-compatible distributed database)
- **Authentication**: JWT Token-based authentication
- **API Documentation**: Auto-generated OpenAPI/Swagger

---

## 🗄️ Database Schema

### Master Tables Overview

Based on the workflow analysis, here are all the required tables:

---

### **1. `users` - User Management**
```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone TEXT,
    profile_image_url TEXT,
    role_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id)
);
```

---

### **2. `roles` - Role Definitions**
```sql
CREATE TABLE roles (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,  -- 'super_admin', 'admin', 'manager', 'technician', 'operator', 'viewer'
    description TEXT,
    level INTEGER NOT NULL,  -- Hierarchy level (1=highest)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Default Roles:**
| Role | Level | Description |
|------|-------|-------------|
| `super_admin` | 1 | Full system access, manages all organizations |
| `admin` | 2 | Organization-level admin, manages users & settings |
| `manager` | 3 | Manages equipment, work orders, and technicians |
| `technician` | 4 | Performs maintenance, updates work orders |
| `operator` | 5 | Views equipment, reports issues |
| `viewer` | 6 | Read-only access |

---

### **3. `permissions` - Permission Definitions**
```sql
CREATE TABLE permissions (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,  -- e.g., 'equipment:create', 'workorder:update'
    resource TEXT NOT NULL,      -- 'equipment', 'workorder', 'user', etc.
    action TEXT NOT NULL,        -- 'create', 'read', 'update', 'delete', 'manage'
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### **4. `role_permissions` - Role-Permission Mapping**
```sql
CREATE TABLE role_permissions (
    id TEXT PRIMARY KEY,
    role_id TEXT NOT NULL,
    permission_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id),
    FOREIGN KEY (permission_id) REFERENCES permissions(id),
    UNIQUE(role_id, permission_id)
);
```

---

### **5. `organizations` - Multi-Tenant Organizations**
```sql
CREATE TABLE organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    logo_url TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    country TEXT,
    postal_code TEXT,
    phone TEXT,
    email TEXT,
    website TEXT,
    subscription_tier TEXT DEFAULT 'free',  -- 'free', 'basic', 'pro', 'enterprise'
    subscription_expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    settings JSON,  -- Organization-specific settings
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### **6. `locations` - Facility/Site Locations**
```sql
CREATE TABLE locations (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    name TEXT NOT NULL,
    code TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    country TEXT,
    postal_code TEXT,
    latitude REAL,
    longitude REAL,
    parent_location_id TEXT,  -- For hierarchical locations
    type TEXT,  -- 'site', 'building', 'floor', 'room', 'area'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (parent_location_id) REFERENCES locations(id)
);
```

---

### **7. `equipment_categories` - Equipment Classification**
```sql
CREATE TABLE equipment_categories (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    name TEXT NOT NULL,
    code TEXT,
    description TEXT,
    parent_category_id TEXT,
    icon TEXT,
    color TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (parent_category_id) REFERENCES equipment_categories(id)
);
```

---

### **8. `equipment` - Main Equipment/Assets Table**
```sql
CREATE TABLE equipment (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    location_id TEXT,
    category_id TEXT,
    name TEXT NOT NULL,
    code TEXT UNIQUE,  -- Equipment/Asset code
    serial_number TEXT,
    model TEXT,
    manufacturer TEXT,
    description TEXT,
    image_url TEXT,
    purchase_date DATE,
    purchase_cost REAL,
    warranty_expiry DATE,
    expected_lifespan_years INTEGER,
    status TEXT DEFAULT 'operational',  -- 'operational', 'maintenance', 'breakdown', 'retired'
    health_score INTEGER DEFAULT 100,  -- 0-100 health percentage
    criticality TEXT DEFAULT 'medium',  -- 'low', 'medium', 'high', 'critical'
    qr_code TEXT,
    specifications JSON,  -- Technical specifications
    documents JSON,  -- Array of document URLs
    custom_fields JSON,
    last_maintenance_date TIMESTAMP,
    next_maintenance_date TIMESTAMP,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (location_id) REFERENCES locations(id),
    FOREIGN KEY (category_id) REFERENCES equipment_categories(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);
```

---

### **9. `maintenance_schedules` - Preventive Maintenance Schedules**
```sql
CREATE TABLE maintenance_schedules (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    equipment_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL,  -- 'preventive', 'predictive', 'condition_based'
    frequency_type TEXT NOT NULL,  -- 'daily', 'weekly', 'monthly', 'yearly', 'meter_based', 'custom'
    frequency_value INTEGER,
    frequency_unit TEXT,  -- 'days', 'weeks', 'months', 'hours', 'km', etc.
    meter_threshold REAL,  -- For meter-based maintenance
    last_performed TIMESTAMP,
    next_due TIMESTAMP,
    estimated_duration_minutes INTEGER,
    priority TEXT DEFAULT 'medium',
    assigned_to TEXT,  -- Default technician
    checklist_template_id TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (equipment_id) REFERENCES equipment(id),
    FOREIGN KEY (assigned_to) REFERENCES users(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (checklist_template_id) REFERENCES checklist_templates(id)
);
```

---

### **10. `work_orders` - Work Order Management**
```sql
CREATE TABLE work_orders (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    equipment_id TEXT NOT NULL,
    schedule_id TEXT,  -- If generated from schedule
    work_order_number TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL,  -- 'preventive', 'corrective', 'emergency', 'inspection'
    status TEXT DEFAULT 'pending',  -- 'pending', 'in_progress', 'on_hold', 'completed', 'cancelled'
    priority TEXT DEFAULT 'medium',  -- 'low', 'medium', 'high', 'critical'
    requested_by TEXT,
    assigned_to TEXT,
    assigned_team_id TEXT,
    due_date TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    estimated_hours REAL,
    actual_hours REAL,
    estimated_cost REAL,
    actual_cost REAL,
    failure_code TEXT,
    root_cause TEXT,
    resolution_notes TEXT,
    checklist_template_id TEXT,
    attachments JSON,  -- Array of attachment URLs
    custom_fields JSON,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (equipment_id) REFERENCES equipment(id),
    FOREIGN KEY (schedule_id) REFERENCES maintenance_schedules(id),
    FOREIGN KEY (requested_by) REFERENCES users(id),
    FOREIGN KEY (assigned_to) REFERENCES users(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (assigned_team_id) REFERENCES teams(id),
    FOREIGN KEY (checklist_template_id) REFERENCES checklist_templates(id)
);
```

---

### **11. `work_order_tasks` - Work Order Task Breakdown**
```sql
CREATE TABLE work_order_tasks (
    id TEXT PRIMARY KEY,
    work_order_id TEXT NOT NULL,
    task_order INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending',  -- 'pending', 'in_progress', 'completed', 'skipped'
    is_required BOOLEAN DEFAULT TRUE,
    completed_by TEXT,
    completed_at TIMESTAMP,
    notes TEXT,
    time_spent_minutes INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id),
    FOREIGN KEY (completed_by) REFERENCES users(id)
);
```

---

### **12. `work_order_comments` - Work Order Communication**
```sql
CREATE TABLE work_order_comments (
    id TEXT PRIMARY KEY,
    work_order_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    comment TEXT NOT NULL,
    attachments JSON,
    is_internal BOOLEAN DEFAULT FALSE,  -- Internal notes vs public comments
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

---

### **13. `teams` - Technician Teams**
```sql
CREATE TABLE teams (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    leader_id TEXT,
    location_id TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (leader_id) REFERENCES users(id),
    FOREIGN KEY (location_id) REFERENCES locations(id)
);
```

---

### **14. `team_members` - Team Membership**
```sql
CREATE TABLE team_members (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT DEFAULT 'member',  -- 'leader', 'member'
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(team_id, user_id)
);
```

---

### **15. `parts_inventory` - Spare Parts Management**
```sql
CREATE TABLE parts_inventory (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    location_id TEXT,
    name TEXT NOT NULL,
    part_number TEXT UNIQUE,
    description TEXT,
    category TEXT,
    manufacturer TEXT,
    unit TEXT DEFAULT 'piece',
    quantity_in_stock INTEGER DEFAULT 0,
    minimum_stock_level INTEGER DEFAULT 0,
    reorder_quantity INTEGER,
    unit_cost REAL,
    last_restock_date DATE,
    storage_location TEXT,
    image_url TEXT,
    specifications JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (location_id) REFERENCES locations(id)
);
```

---

### **16. `parts_usage` - Parts Consumption Tracking**
```sql
CREATE TABLE parts_usage (
    id TEXT PRIMARY KEY,
    work_order_id TEXT NOT NULL,
    part_id TEXT NOT NULL,
    quantity_used INTEGER NOT NULL,
    unit_cost_at_time REAL,
    used_by TEXT NOT NULL,
    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id),
    FOREIGN KEY (part_id) REFERENCES parts_inventory(id),
    FOREIGN KEY (used_by) REFERENCES users(id)
);
```

---

### **17. `equipment_parts` - Equipment-Part Association**
```sql
CREATE TABLE equipment_parts (
    id TEXT PRIMARY KEY,
    equipment_id TEXT NOT NULL,
    part_id TEXT NOT NULL,
    quantity_required INTEGER DEFAULT 1,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (equipment_id) REFERENCES equipment(id),
    FOREIGN KEY (part_id) REFERENCES parts_inventory(id),
    UNIQUE(equipment_id, part_id)
);
```

---

### **18. `meter_readings` - Equipment Meter Tracking**
```sql
CREATE TABLE meter_readings (
    id TEXT PRIMARY KEY,
    equipment_id TEXT NOT NULL,
    meter_type TEXT NOT NULL,  -- 'hours', 'km', 'cycles', 'units_produced'
    reading_value REAL NOT NULL,
    reading_unit TEXT,
    recorded_by TEXT NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (equipment_id) REFERENCES equipment(id),
    FOREIGN KEY (recorded_by) REFERENCES users(id)
);
```

---

### **19. `checklist_templates` - Reusable Checklists**
```sql
CREATE TABLE checklist_templates (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    items JSON NOT NULL,  -- Array of checklist items with order, title, type, options
    is_active BOOLEAN DEFAULT TRUE,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);
```

---

### **20. `work_order_checklists` - Completed Checklists**
```sql
CREATE TABLE work_order_checklists (
    id TEXT PRIMARY KEY,
    work_order_id TEXT NOT NULL,
    template_id TEXT,
    responses JSON NOT NULL,  -- Array of responses matching template items
    completed_by TEXT,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id),
    FOREIGN KEY (template_id) REFERENCES checklist_templates(id),
    FOREIGN KEY (completed_by) REFERENCES users(id)
);
```

---

### **21. `maintenance_history` - Equipment Maintenance Log**
```sql
CREATE TABLE maintenance_history (
    id TEXT PRIMARY KEY,
    equipment_id TEXT NOT NULL,
    work_order_id TEXT,
    action_type TEXT NOT NULL,  -- 'maintenance', 'repair', 'inspection', 'replacement'
    summary TEXT NOT NULL,
    details TEXT,
    performed_by TEXT,
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cost REAL,
    downtime_minutes INTEGER,
    parts_used JSON,
    before_status TEXT,
    after_status TEXT,
    before_health_score INTEGER,
    after_health_score INTEGER,
    FOREIGN KEY (equipment_id) REFERENCES equipment(id),
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id),
    FOREIGN KEY (performed_by) REFERENCES users(id)
);
```

---

### **22. `notifications` - User Notifications**
```sql
CREATE TABLE notifications (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    type TEXT NOT NULL,  -- 'work_order', 'maintenance_due', 'low_stock', 'system', etc.
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    reference_type TEXT,  -- 'work_order', 'equipment', 'part', etc.
    reference_id TEXT,
    priority TEXT DEFAULT 'normal',
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    action_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id)
);
```

---

### **23. `audit_logs` - System Audit Trail**
```sql
CREATE TABLE audit_logs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    user_id TEXT,
    action TEXT NOT NULL,  -- 'create', 'update', 'delete', 'login', 'logout', etc.
    resource_type TEXT NOT NULL,  -- 'equipment', 'work_order', 'user', etc.
    resource_id TEXT,
    old_values JSON,
    new_values JSON,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

---

### **24. `sessions` - User Sessions (JWT Token Management)**
```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    refresh_token_hash TEXT NOT NULL,
    device_info TEXT,
    ip_address TEXT,
    user_agent TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

---

### **25. `password_reset_tokens` - Password Recovery**
```sql
CREATE TABLE password_reset_tokens (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    token_hash TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

---

### **26. `reports` - Saved Reports**
```sql
CREATE TABLE reports (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL,  -- 'equipment_health', 'work_order_summary', 'maintenance_costs', etc.
    parameters JSON,  -- Report parameters/filters
    schedule TEXT,  -- Cron expression for scheduled reports
    recipients JSON,  -- Array of user IDs or emails
    last_generated TIMESTAMP,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);
```

---

### **27. `dashboards` - Custom Dashboards**
```sql
CREATE TABLE dashboards (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    user_id TEXT,  -- NULL for organization-wide dashboards
    name TEXT NOT NULL,
    layout JSON NOT NULL,  -- Dashboard widget configuration
    is_default BOOLEAN DEFAULT FALSE,
    is_public BOOLEAN DEFAULT FALSE,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);
```

---

## 🔐 Role-Based Access Control (RBAC)

### Permission Matrix

| Resource | Super Admin | Admin | Manager | Technician | Operator | Viewer |
|----------|-------------|-------|---------|------------|----------|--------|
| **Organizations** | CRUD | Read Own | Read Own | Read Own | Read Own | Read Own |
| **Users** | CRUD All | CRUD Org | Read Team | Read Self | Read Self | Read Self |
| **Equipment** | CRUD All | CRUD Org | CRUD Loc | Read+Update | Read+Report | Read |
| **Work Orders** | CRUD All | CRUD Org | CRUD | CRUD Assigned | Create | Read |
| **Schedules** | CRUD All | CRUD Org | CRUD | Read | Read | Read |
| **Parts** | CRUD All | CRUD Org | CRUD | Update Stock | Read | Read |
| **Reports** | CRUD All | CRUD Org | CRUD | Read | Read | Read |
| **Audit Logs** | Read All | Read Org | Read Own | Read Own | - | - |

### Permission Definitions

```python
PERMISSIONS = {
    # Organization
    "organization:create": "Create new organizations",
    "organization:read": "View organization details",
    "organization:update": "Update organization settings",
    "organization:delete": "Delete organizations",
    
    # Users
    "user:create": "Create new users",
    "user:read": "View user profiles",
    "user:update": "Update user information",
    "user:delete": "Delete users",
    "user:manage_roles": "Assign/change user roles",
    
    # Equipment
    "equipment:create": "Add new equipment",
    "equipment:read": "View equipment details",
    "equipment:update": "Update equipment information",
    "equipment:delete": "Delete equipment",
    "equipment:report_issue": "Report equipment issues",
    
    # Work Orders
    "workorder:create": "Create work orders",
    "workorder:read": "View work orders",
    "workorder:update": "Update work orders",
    "workorder:delete": "Delete work orders",
    "workorder:assign": "Assign work orders",
    "workorder:complete": "Complete work orders",
    
    # Maintenance Schedules
    "schedule:create": "Create maintenance schedules",
    "schedule:read": "View schedules",
    "schedule:update": "Update schedules",
    "schedule:delete": "Delete schedules",
    
    # Parts/Inventory
    "parts:create": "Add new parts",
    "parts:read": "View parts inventory",
    "parts:update": "Update parts information",
    "parts:delete": "Delete parts",
    "parts:use": "Use parts from inventory",
    
    # Reports
    "report:create": "Create reports",
    "report:read": "View reports",
    "report:update": "Update reports",
    "report:delete": "Delete reports",
    "report:export": "Export reports",
    
    # Settings & Admin
    "settings:manage": "Manage organization settings",
    "audit:read": "View audit logs",
    "notification:manage": "Manage notification settings",
}
```

---

## 🌐 API Endpoints

### Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/api/v1/auth/register` | Register new user | No |
| `POST` | `/api/v1/auth/login` | User login | No |
| `POST` | `/api/v1/auth/logout` | User logout | Yes |
| `POST` | `/api/v1/auth/refresh` | Refresh access token | Yes (Refresh Token) |
| `POST` | `/api/v1/auth/forgot-password` | Request password reset | No |
| `POST` | `/api/v1/auth/reset-password` | Reset password with token | No |
| `GET` | `/api/v1/auth/verify-email/{token}` | Verify email address | No |
| `GET` | `/api/v1/auth/me` | Get current user profile | Yes |
| `PUT` | `/api/v1/auth/me` | Update current user profile | Yes |
| `PUT` | `/api/v1/auth/me/password` | Change password | Yes |

---

### Organization Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| `POST` | `/api/v1/organizations` | Create organization | `organization:create` |
| `GET` | `/api/v1/organizations` | List organizations | `organization:read` |
| `GET` | `/api/v1/organizations/{id}` | Get organization details | `organization:read` |
| `PUT` | `/api/v1/organizations/{id}` | Update organization | `organization:update` |
| `DELETE` | `/api/v1/organizations/{id}` | Delete organization | `organization:delete` |
| `GET` | `/api/v1/organizations/{id}/stats` | Get organization statistics | `organization:read` |

---

### User Management Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| `POST` | `/api/v1/users` | Create user | `user:create` |
| `GET` | `/api/v1/users` | List users (with filters) | `user:read` |
| `GET` | `/api/v1/users/{id}` | Get user details | `user:read` |
| `PUT` | `/api/v1/users/{id}` | Update user | `user:update` |
| `DELETE` | `/api/v1/users/{id}` | Delete/deactivate user | `user:delete` |
| `PUT` | `/api/v1/users/{id}/role` | Change user role | `user:manage_roles` |
| `GET` | `/api/v1/users/{id}/workorders` | Get user's work orders | `user:read` |
| `GET` | `/api/v1/users/{id}/activity` | Get user activity log | `user:read` |

---

### Location Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| `POST` | `/api/v1/locations` | Create location | `equipment:create` |
| `GET` | `/api/v1/locations` | List locations | `equipment:read` |
| `GET` | `/api/v1/locations/{id}` | Get location details | `equipment:read` |
| `PUT` | `/api/v1/locations/{id}` | Update location | `equipment:update` |
| `DELETE` | `/api/v1/locations/{id}` | Delete location | `equipment:delete` |
| `GET` | `/api/v1/locations/{id}/equipment` | Get equipment at location | `equipment:read` |

---

### Equipment Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| `POST` | `/api/v1/equipment` | Create equipment | `equipment:create` |
| `GET` | `/api/v1/equipment` | List equipment (with filters) | `equipment:read` |
| `GET` | `/api/v1/equipment/{id}` | Get equipment details | `equipment:read` |
| `PUT` | `/api/v1/equipment/{id}` | Update equipment | `equipment:update` |
| `DELETE` | `/api/v1/equipment/{id}` | Delete equipment | `equipment:delete` |
| `GET` | `/api/v1/equipment/{id}/history` | Get maintenance history | `equipment:read` |
| `GET` | `/api/v1/equipment/{id}/workorders` | Get related work orders | `workorder:read` |
| `GET` | `/api/v1/equipment/{id}/schedules` | Get maintenance schedules | `schedule:read` |
| `GET` | `/api/v1/equipment/{id}/parts` | Get associated parts | `parts:read` |
| `POST` | `/api/v1/equipment/{id}/meter-reading` | Add meter reading | `equipment:update` |
| `GET` | `/api/v1/equipment/{id}/meter-readings` | Get meter readings | `equipment:read` |
| `POST` | `/api/v1/equipment/{id}/report-issue` | Report equipment issue | `equipment:report_issue` |
| `GET` | `/api/v1/equipment/{id}/qr` | Generate QR code | `equipment:read` |

---

### Equipment Category Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| `POST` | `/api/v1/categories` | Create category | `equipment:create` |
| `GET` | `/api/v1/categories` | List categories | `equipment:read` |
| `GET` | `/api/v1/categories/{id}` | Get category details | `equipment:read` |
| `PUT` | `/api/v1/categories/{id}` | Update category | `equipment:update` |
| `DELETE` | `/api/v1/categories/{id}` | Delete category | `equipment:delete` |

---

### Maintenance Schedule Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| `POST` | `/api/v1/schedules` | Create schedule | `schedule:create` |
| `GET` | `/api/v1/schedules` | List schedules | `schedule:read` |
| `GET` | `/api/v1/schedules/{id}` | Get schedule details | `schedule:read` |
| `PUT` | `/api/v1/schedules/{id}` | Update schedule | `schedule:update` |
| `DELETE` | `/api/v1/schedules/{id}` | Delete schedule | `schedule:delete` |
| `POST` | `/api/v1/schedules/{id}/generate-workorder` | Generate work order | `workorder:create` |
| `GET` | `/api/v1/schedules/upcoming` | Get upcoming maintenance | `schedule:read` |
| `GET` | `/api/v1/schedules/overdue` | Get overdue maintenance | `schedule:read` |

---

### Work Order Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| `POST` | `/api/v1/workorders` | Create work order | `workorder:create` |
| `GET` | `/api/v1/workorders` | List work orders (with filters) | `workorder:read` |
| `GET` | `/api/v1/workorders/{id}` | Get work order details | `workorder:read` |
| `PUT` | `/api/v1/workorders/{id}` | Update work order | `workorder:update` |
| `DELETE` | `/api/v1/workorders/{id}` | Delete work order | `workorder:delete` |
| `PUT` | `/api/v1/workorders/{id}/status` | Update status | `workorder:update` |
| `PUT` | `/api/v1/workorders/{id}/assign` | Assign work order | `workorder:assign` |
| `POST` | `/api/v1/workorders/{id}/start` | Start work order | `workorder:update` |
| `POST` | `/api/v1/workorders/{id}/complete` | Complete work order | `workorder:complete` |
| `POST` | `/api/v1/workorders/{id}/hold` | Put on hold | `workorder:update` |
| `POST` | `/api/v1/workorders/{id}/cancel` | Cancel work order | `workorder:update` |
| `GET` | `/api/v1/workorders/{id}/tasks` | Get tasks | `workorder:read` |
| `PUT` | `/api/v1/workorders/{id}/tasks/{task_id}` | Update task | `workorder:update` |
| `GET` | `/api/v1/workorders/{id}/comments` | Get comments | `workorder:read` |
| `POST` | `/api/v1/workorders/{id}/comments` | Add comment | `workorder:update` |
| `POST` | `/api/v1/workorders/{id}/parts` | Add parts used | `parts:use` |
| `GET` | `/api/v1/workorders/{id}/checklist` | Get checklist | `workorder:read` |
| `PUT` | `/api/v1/workorders/{id}/checklist` | Update checklist | `workorder:update` |

---

### Team Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| `POST` | `/api/v1/teams` | Create team | `user:manage_roles` |
| `GET` | `/api/v1/teams` | List teams | `user:read` |
| `GET` | `/api/v1/teams/{id}` | Get team details | `user:read` |
| `PUT` | `/api/v1/teams/{id}` | Update team | `user:manage_roles` |
| `DELETE` | `/api/v1/teams/{id}` | Delete team | `user:manage_roles` |
| `POST` | `/api/v1/teams/{id}/members` | Add team member | `user:manage_roles` |
| `DELETE` | `/api/v1/teams/{id}/members/{user_id}` | Remove member | `user:manage_roles` |
| `GET` | `/api/v1/teams/{id}/workorders` | Get team's work orders | `workorder:read` |

---

### Parts/Inventory Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| `POST` | `/api/v1/parts` | Create part | `parts:create` |
| `GET` | `/api/v1/parts` | List parts (with filters) | `parts:read` |
| `GET` | `/api/v1/parts/{id}` | Get part details | `parts:read` |
| `PUT` | `/api/v1/parts/{id}` | Update part | `parts:update` |
| `DELETE` | `/api/v1/parts/{id}` | Delete part | `parts:delete` |
| `POST` | `/api/v1/parts/{id}/adjust-stock` | Adjust stock level | `parts:update` |
| `GET` | `/api/v1/parts/{id}/usage-history` | Get usage history | `parts:read` |
| `GET` | `/api/v1/parts/low-stock` | Get low stock alerts | `parts:read` |
| `POST` | `/api/v1/parts/{id}/equipment` | Link part to equipment | `parts:update` |

---

### Checklist Template Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| `POST` | `/api/v1/checklists` | Create template | `schedule:create` |
| `GET` | `/api/v1/checklists` | List templates | `schedule:read` |
| `GET` | `/api/v1/checklists/{id}` | Get template details | `schedule:read` |
| `PUT` | `/api/v1/checklists/{id}` | Update template | `schedule:update` |
| `DELETE` | `/api/v1/checklists/{id}` | Delete template | `schedule:delete` |

---

### Notification Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| `GET` | `/api/v1/notifications` | Get user notifications | Always (own) |
| `PUT` | `/api/v1/notifications/{id}/read` | Mark as read | Always (own) |
| `PUT` | `/api/v1/notifications/read-all` | Mark all as read | Always (own) |
| `DELETE` | `/api/v1/notifications/{id}` | Delete notification | Always (own) |
| `GET` | `/api/v1/notifications/settings` | Get notification settings | Always (own) |
| `PUT` | `/api/v1/notifications/settings` | Update settings | Always (own) |

---

### Reports & Analytics Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| `GET` | `/api/v1/reports/dashboard` | Get dashboard data | `report:read` |
| `GET` | `/api/v1/reports/equipment-health` | Equipment health report | `report:read` |
| `GET` | `/api/v1/reports/workorder-summary` | Work order summary | `report:read` |
| `GET` | `/api/v1/reports/maintenance-costs` | Maintenance cost report | `report:read` |
| `GET` | `/api/v1/reports/technician-performance` | Technician performance | `report:read` |
| `GET` | `/api/v1/reports/downtime` | Downtime analysis | `report:read` |
| `GET` | `/api/v1/reports/parts-usage` | Parts usage report | `report:read` |
| `POST` | `/api/v1/reports/custom` | Generate custom report | `report:create` |
| `GET` | `/api/v1/reports/saved` | Get saved reports | `report:read` |
| `POST` | `/api/v1/reports/saved` | Save report | `report:create` |
| `GET` | `/api/v1/reports/export/{format}` | Export report (PDF/Excel) | `report:export` |

---

### Audit Log Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| `GET` | `/api/v1/audit-logs` | Get audit logs | `audit:read` |
| `GET` | `/api/v1/audit-logs/{resource}/{id}` | Get resource audit trail | `audit:read` |

---

### Dashboard Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| `GET` | `/api/v1/dashboards` | Get user dashboards | Always (own) |
| `POST` | `/api/v1/dashboards` | Create dashboard | Always (own) |
| `GET` | `/api/v1/dashboards/{id}` | Get dashboard | Always (own) |
| `PUT` | `/api/v1/dashboards/{id}` | Update dashboard | Always (own) |
| `DELETE` | `/api/v1/dashboards/{id}` | Delete dashboard | Always (own) |

---

## 🔑 Authentication Flow

### JWT Token Structure

```python
# Access Token Payload
{
    "sub": "user_id",
    "email": "user@example.com",
    "org_id": "organization_id",
    "role": "manager",
    "permissions": ["equipment:read", "workorder:create", ...],
    "exp": 1703673600,  # 15 minutes
    "iat": 1703672700,
    "type": "access"
}

# Refresh Token Payload
{
    "sub": "user_id",
    "session_id": "session_id",
    "exp": 1704277500,  # 7 days
    "iat": 1703672700,
    "type": "refresh"
}
```

### Authentication Middleware Flow

```
1. Request arrives at protected endpoint
2. Extract JWT from Authorization header (Bearer token)
3. Validate token signature and expiration
4. Extract user_id, org_id, permissions from token
5. Check if user has required permission for endpoint
6. If permission check passes, proceed to handler
7. If any check fails, return 401/403 error
```

---

## 📁 Project Structure

```
gearguard-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry
│   ├── config.py               # Configuration settings
│   ├── database.py             # Turso/libSQL connection
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py             # Dependency injection
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py       # Main API router
│   │       ├── auth.py         # Authentication endpoints
│   │       ├── users.py        # User management
│   │       ├── organizations.py
│   │       ├── locations.py
│   │       ├── equipment.py
│   │       ├── categories.py
│   │       ├── schedules.py
│   │       ├── workorders.py
│   │       ├── teams.py
│   │       ├── parts.py
│   │       ├── checklists.py
│   │       ├── notifications.py
│   │       ├── reports.py
│   │       ├── dashboards.py
│   │       └── audit.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py         # JWT handling, password hashing
│   │   ├── permissions.py      # RBAC implementation
│   │   └── exceptions.py       # Custom exceptions
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── organization.py
│   │   ├── equipment.py
│   │   ├── workorder.py
│   │   ├── schedule.py
│   │   ├── part.py
│   │   ├── team.py
│   │   ├── notification.py
│   │   └── audit.py
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py             # Pydantic schemas for auth
│   │   ├── user.py
│   │   ├── organization.py
│   │   ├── equipment.py
│   │   ├── workorder.py
│   │   ├── schedule.py
│   │   ├── part.py
│   │   ├── team.py
│   │   ├── notification.py
│   │   ├── report.py
│   │   └── common.py           # Shared schemas
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── equipment_service.py
│   │   ├── workorder_service.py
│   │   ├── schedule_service.py
│   │   ├── notification_service.py
│   │   ├── report_service.py
│   │   └── audit_service.py
│   │
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base.py             # Base repository pattern
│   │   ├── user_repo.py
│   │   ├── equipment_repo.py
│   │   ├── workorder_repo.py
│   │   └── ...
│   │
│   └── utils/
│       ├── __init__.py
│       ├── id_generator.py     # UUID/ULID generation
│       ├── qr_code.py          # QR code generation
│       ├── email.py            # Email utilities
│       └── validators.py       # Custom validators
│
├── migrations/
│   ├── __init__.py
│   └── versions/               # Database migrations
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_users.py
│   ├── test_equipment.py
│   └── ...
│
├── .env.example
├── .gitignore
├── requirements.txt
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 🚀 Implementation Guide

### Step 1: Project Setup

```bash
# Create project directory
mkdir gearguard-backend && cd gearguard-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install fastapi uvicorn libsql python-jose[cryptography] passlib[bcrypt] python-multipart pydantic-settings python-dotenv ulid-py qrcode pillow
```

### Step 2: Environment Configuration

```env
# .env
APP_NAME=GearGuard
APP_ENV=development
DEBUG=true

# Turso Database
TURSO_DATABASE_URL=libsql://your-db.turso.io
TURSO_AUTH_TOKEN=your-auth-token

# JWT Configuration
JWT_SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Email (optional)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your-email
SMTP_PASSWORD=your-password

# CORS
CORS_ORIGINS=["http://localhost:3000"]
```

### Step 3: Database Connection (Turso)

```python
# app/database.py
import os
import libsql
from functools import lru_cache

class Database:
    def __init__(self):
        self.url = os.getenv("TURSO_DATABASE_URL")
        self.auth_token = os.getenv("TURSO_AUTH_TOKEN")
        self._connection = None
    
    def connect(self):
        if self._connection is None:
            self._connection = libsql.connect(
                "local.db",  # Local replica
                sync_url=self.url,
                auth_token=self.auth_token
            )
            self._connection.sync()
        return self._connection
    
    def execute(self, query: str, params: tuple = ()):
        conn = self.connect()
        return conn.execute(query, params)
    
    def sync(self):
        if self._connection:
            self._connection.sync()

@lru_cache()
def get_database() -> Database:
    return Database()
```

### Step 4: Core Security Module

```python
# app/core/security.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class TokenData(BaseModel):
    user_id: str
    email: str
    org_id: str
    role: str
    permissions: list[str]
    type: str

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(
        to_encode,
        os.getenv("JWT_SECRET_KEY"),
        algorithm=os.getenv("JWT_ALGORITHM", "HS256")
    )

def create_refresh_token(user_id: str, session_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode = {
        "sub": user_id,
        "session_id": session_id,
        "exp": expire,
        "type": "refresh"
    }
    return jwt.encode(
        to_encode,
        os.getenv("JWT_SECRET_KEY"),
        algorithm=os.getenv("JWT_ALGORITHM", "HS256")
    )

def decode_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(
            token,
            os.getenv("JWT_SECRET_KEY"),
            algorithms=[os.getenv("JWT_ALGORITHM", "HS256")]
        )
        return TokenData(**payload)
    except JWTError:
        return None
```

### Step 5: RBAC Permission System

```python
# app/core/permissions.py
from functools import wraps
from fastapi import HTTPException, Depends
from .security import TokenData

ROLE_PERMISSIONS = {
    "super_admin": ["*"],  # All permissions
    "admin": [
        "organization:read", "organization:update",
        "user:*", "equipment:*", "workorder:*",
        "schedule:*", "parts:*", "report:*",
        "settings:manage", "audit:read"
    ],
    "manager": [
        "user:read", "equipment:*", "workorder:*",
        "schedule:*", "parts:*", "report:*"
    ],
    "technician": [
        "equipment:read", "equipment:update",
        "workorder:read", "workorder:update", "workorder:complete",
        "schedule:read", "parts:read", "parts:use"
    ],
    "operator": [
        "equipment:read", "equipment:report_issue",
        "workorder:create", "workorder:read",
        "schedule:read", "parts:read"
    ],
    "viewer": [
        "equipment:read", "workorder:read",
        "schedule:read", "parts:read", "report:read"
    ]
}

def has_permission(user_permissions: list[str], required_permission: str) -> bool:
    # Super admin can do anything
    if "*" in user_permissions:
        return True
    
    # Check exact match
    if required_permission in user_permissions:
        return True
    
    # Check wildcard (e.g., "equipment:*" matches "equipment:read")
    resource = required_permission.split(":")[0]
    if f"{resource}:*" in user_permissions:
        return True
    
    return False

def require_permission(permission: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: TokenData = None, **kwargs):
            if current_user is None:
                raise HTTPException(status_code=401, detail="Not authenticated")
            
            if not has_permission(current_user.permissions, permission):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {permission} required"
                )
            
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator
```

### Step 6: Main FastAPI Application

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from .config import settings
from .database import get_database
from .api.v1.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database connection
    db = get_database()
    db.connect()
    print("Database connected successfully!")
    yield
    # Shutdown: Cleanup
    db.sync()
    print("Database synced and connection closed.")

app = FastAPI(
    title="GearGuard API",
    description="The Ultimate Maintenance Tracker Backend",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "message": "Welcome to GearGuard API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

---

## 📊 Workflow Navigation Mapping

Based on the user navigation workflow image:

### User Journey → API Flow

| Screen | APIs Used |
|--------|-----------|
| **Login/Register** | `POST /auth/login`, `POST /auth/register` |
| **Dashboard** | `GET /reports/dashboard`, `GET /notifications` |
| **Equipment List** | `GET /equipment`, `GET /categories` |
| **Equipment Detail** | `GET /equipment/{id}`, `GET /equipment/{id}/history` |
| **Add Equipment** | `POST /equipment`, `GET /locations`, `GET /categories` |
| **Work Order List** | `GET /workorders`, filters by status |
| **Work Order Detail** | `GET /workorders/{id}`, `GET /workorders/{id}/tasks` |
| **Create Work Order** | `POST /workorders`, `GET /equipment`, `GET /users` |
| **Maintenance Schedule** | `GET /schedules`, `GET /schedules/upcoming` |
| **Parts Inventory** | `GET /parts`, `GET /parts/low-stock` |
| **Reports** | `GET /reports/*` endpoints |
| **Settings** | `PUT /organizations/{id}`, `GET /users` |
| **User Profile** | `GET /auth/me`, `PUT /auth/me` |

---

## 🎯 Next Steps for Your Team

1. **Database Setup**: Create Turso database and run migration scripts
2. **Core Implementation**: Start with auth, users, and organizations
3. **Equipment Module**: Implement equipment CRUD with categories and locations
4. **Work Orders**: Build work order system with task management
5. **Notifications**: Implement real-time notifications (consider WebSocket)
6. **Reports**: Create analytics and reporting endpoints
7. **Testing**: Write unit and integration tests
8. **Documentation**: Generate OpenAPI docs automatically

---

## 📝 Notes for Team Collaboration

- Use **Pydantic v2** for request/response validation
- Implement **repository pattern** for database operations
- Use **dependency injection** for services
- Add **logging** throughout the application
- Consider **Redis** for caching if needed
- Use **Alembic** or custom migration scripts for database versioning

---

**Document Version**: 1.0.0  
**Last Updated**: December 27, 2024  
**Author**: GearGuard Backend Team
