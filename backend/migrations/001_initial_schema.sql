-- ============================================
-- GearGuard Database Schema
-- Migration: 001_initial_schema
-- Created: 2024-12-27
-- Database: Turso (LibSQL/SQLite Compatible)
-- ============================================

-- Enable foreign key support
PRAGMA foreign_keys = ON;

-- ============================================
-- CORE TABLES
-- ============================================

-- 1. Roles Table
CREATE TABLE IF NOT EXISTS roles (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    level INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Permissions Table
CREATE TABLE IF NOT EXISTS permissions (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    resource TEXT NOT NULL,
    action TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Role-Permissions Mapping
CREATE TABLE IF NOT EXISTS role_permissions (
    id TEXT PRIMARY KEY,
    role_id TEXT NOT NULL,
    permission_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE,
    UNIQUE(role_id, permission_id)
);

-- 4. Organizations Table
CREATE TABLE IF NOT EXISTS organizations (
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
    subscription_tier TEXT DEFAULT 'free',
    subscription_expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    settings TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Users Table
CREATE TABLE IF NOT EXISTS users (
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

-- 6. Sessions Table
CREATE TABLE IF NOT EXISTS sessions (
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
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 7. Password Reset Tokens
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    token_hash TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ============================================
-- LOCATION & EQUIPMENT TABLES
-- ============================================

-- 8. Locations Table
CREATE TABLE IF NOT EXISTS locations (
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
    parent_location_id TEXT,
    type TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_location_id) REFERENCES locations(id)
);

-- 9. Equipment Categories Table
CREATE TABLE IF NOT EXISTS equipment_categories (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    name TEXT NOT NULL,
    code TEXT,
    description TEXT,
    parent_category_id TEXT,
    icon TEXT,
    color TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_category_id) REFERENCES equipment_categories(id)
);

-- 10. Equipment Table
CREATE TABLE IF NOT EXISTS equipment (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    location_id TEXT,
    category_id TEXT,
    name TEXT NOT NULL,
    code TEXT UNIQUE,
    serial_number TEXT,
    model TEXT,
    manufacturer TEXT,
    description TEXT,
    image_url TEXT,
    purchase_date DATE,
    purchase_cost REAL,
    warranty_expiry DATE,
    expected_lifespan_years INTEGER,
    status TEXT DEFAULT 'operational',
    health_score INTEGER DEFAULT 100,
    criticality TEXT DEFAULT 'medium',
    qr_code TEXT,
    specifications TEXT,
    documents TEXT,
    custom_fields TEXT,
    last_maintenance_date TIMESTAMP,
    next_maintenance_date TIMESTAMP,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (location_id) REFERENCES locations(id),
    FOREIGN KEY (category_id) REFERENCES equipment_categories(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- 11. Meter Readings Table
CREATE TABLE IF NOT EXISTS meter_readings (
    id TEXT PRIMARY KEY,
    equipment_id TEXT NOT NULL,
    meter_type TEXT NOT NULL,
    reading_value REAL NOT NULL,
    reading_unit TEXT,
    recorded_by TEXT NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (equipment_id) REFERENCES equipment(id) ON DELETE CASCADE,
    FOREIGN KEY (recorded_by) REFERENCES users(id)
);

-- ============================================
-- TEAM MANAGEMENT TABLES
-- ============================================

-- 12. Teams Table
CREATE TABLE IF NOT EXISTS teams (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    leader_id TEXT,
    location_id TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (leader_id) REFERENCES users(id),
    FOREIGN KEY (location_id) REFERENCES locations(id)
);

-- 13. Team Members Table
CREATE TABLE IF NOT EXISTS team_members (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT DEFAULT 'member',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(team_id, user_id)
);

-- ============================================
-- CHECKLIST TABLES
-- ============================================

-- 14. Checklist Templates Table
CREATE TABLE IF NOT EXISTS checklist_templates (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    items TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- ============================================
-- MAINTENANCE SCHEDULE TABLES
-- ============================================

-- 15. Maintenance Schedules Table
CREATE TABLE IF NOT EXISTS maintenance_schedules (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    equipment_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL,
    frequency_type TEXT NOT NULL,
    frequency_value INTEGER,
    frequency_unit TEXT,
    meter_threshold REAL,
    last_performed TIMESTAMP,
    next_due TIMESTAMP,
    estimated_duration_minutes INTEGER,
    priority TEXT DEFAULT 'medium',
    assigned_to TEXT,
    checklist_template_id TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (equipment_id) REFERENCES equipment(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_to) REFERENCES users(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (checklist_template_id) REFERENCES checklist_templates(id)
);

-- ============================================
-- WORK ORDER TABLES
-- ============================================

-- 16. Work Orders Table
CREATE TABLE IF NOT EXISTS work_orders (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    equipment_id TEXT NOT NULL,
    schedule_id TEXT,
    work_order_number TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    priority TEXT DEFAULT 'medium',
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
    attachments TEXT,
    custom_fields TEXT,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (equipment_id) REFERENCES equipment(id),
    FOREIGN KEY (schedule_id) REFERENCES maintenance_schedules(id),
    FOREIGN KEY (requested_by) REFERENCES users(id),
    FOREIGN KEY (assigned_to) REFERENCES users(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (assigned_team_id) REFERENCES teams(id),
    FOREIGN KEY (checklist_template_id) REFERENCES checklist_templates(id)
);

-- 17. Work Order Tasks Table
CREATE TABLE IF NOT EXISTS work_order_tasks (
    id TEXT PRIMARY KEY,
    work_order_id TEXT NOT NULL,
    task_order INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending',
    is_required BOOLEAN DEFAULT TRUE,
    completed_by TEXT,
    completed_at TIMESTAMP,
    notes TEXT,
    time_spent_minutes INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (completed_by) REFERENCES users(id)
);

-- 18. Work Order Comments Table
CREATE TABLE IF NOT EXISTS work_order_comments (
    id TEXT PRIMARY KEY,
    work_order_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    comment TEXT NOT NULL,
    attachments TEXT,
    is_internal BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 19. Work Order Checklists Table
CREATE TABLE IF NOT EXISTS work_order_checklists (
    id TEXT PRIMARY KEY,
    work_order_id TEXT NOT NULL,
    template_id TEXT,
    responses TEXT NOT NULL,
    completed_by TEXT,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (template_id) REFERENCES checklist_templates(id),
    FOREIGN KEY (completed_by) REFERENCES users(id)
);

-- ============================================
-- PARTS/INVENTORY TABLES
-- ============================================

-- 20. Parts Inventory Table
CREATE TABLE IF NOT EXISTS parts_inventory (
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
    specifications TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (location_id) REFERENCES locations(id)
);

-- 21. Parts Usage Table
CREATE TABLE IF NOT EXISTS parts_usage (
    id TEXT PRIMARY KEY,
    work_order_id TEXT NOT NULL,
    part_id TEXT NOT NULL,
    quantity_used INTEGER NOT NULL,
    unit_cost_at_time REAL,
    used_by TEXT NOT NULL,
    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (part_id) REFERENCES parts_inventory(id),
    FOREIGN KEY (used_by) REFERENCES users(id)
);

-- 22. Equipment Parts Association Table
CREATE TABLE IF NOT EXISTS equipment_parts (
    id TEXT PRIMARY KEY,
    equipment_id TEXT NOT NULL,
    part_id TEXT NOT NULL,
    quantity_required INTEGER DEFAULT 1,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (equipment_id) REFERENCES equipment(id) ON DELETE CASCADE,
    FOREIGN KEY (part_id) REFERENCES parts_inventory(id) ON DELETE CASCADE,
    UNIQUE(equipment_id, part_id)
);

-- ============================================
-- HISTORY & LOGGING TABLES
-- ============================================

-- 23. Maintenance History Table
CREATE TABLE IF NOT EXISTS maintenance_history (
    id TEXT PRIMARY KEY,
    equipment_id TEXT NOT NULL,
    work_order_id TEXT,
    action_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    details TEXT,
    performed_by TEXT,
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cost REAL,
    downtime_minutes INTEGER,
    parts_used TEXT,
    before_status TEXT,
    after_status TEXT,
    before_health_score INTEGER,
    after_health_score INTEGER,
    FOREIGN KEY (equipment_id) REFERENCES equipment(id) ON DELETE CASCADE,
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id),
    FOREIGN KEY (performed_by) REFERENCES users(id)
);

-- 24. Audit Logs Table
CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    user_id TEXT,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    old_values TEXT,
    new_values TEXT,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ============================================
-- NOTIFICATION TABLES
-- ============================================

-- 25. Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    reference_type TEXT,
    reference_id TEXT,
    priority TEXT DEFAULT 'normal',
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    action_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

-- ============================================
-- REPORTING TABLES
-- ============================================

-- 26. Reports Table
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL,
    parameters TEXT,
    schedule TEXT,
    recipients TEXT,
    last_generated TIMESTAMP,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- 27. Dashboards Table
CREATE TABLE IF NOT EXISTS dashboards (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    user_id TEXT,
    name TEXT NOT NULL,
    layout TEXT NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    is_public BOOLEAN DEFAULT FALSE,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

-- Users indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_organization ON users(organization_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role_id);

-- Equipment indexes
CREATE INDEX IF NOT EXISTS idx_equipment_organization ON equipment(organization_id);
CREATE INDEX IF NOT EXISTS idx_equipment_location ON equipment(location_id);
CREATE INDEX IF NOT EXISTS idx_equipment_category ON equipment(category_id);
CREATE INDEX IF NOT EXISTS idx_equipment_status ON equipment(status);
CREATE INDEX IF NOT EXISTS idx_equipment_code ON equipment(code);

-- Work Orders indexes
CREATE INDEX IF NOT EXISTS idx_workorders_organization ON work_orders(organization_id);
CREATE INDEX IF NOT EXISTS idx_workorders_equipment ON work_orders(equipment_id);
CREATE INDEX IF NOT EXISTS idx_workorders_status ON work_orders(status);
CREATE INDEX IF NOT EXISTS idx_workorders_assigned_to ON work_orders(assigned_to);
CREATE INDEX IF NOT EXISTS idx_workorders_due_date ON work_orders(due_date);
CREATE INDEX IF NOT EXISTS idx_workorders_number ON work_orders(work_order_number);

-- Maintenance Schedules indexes
CREATE INDEX IF NOT EXISTS idx_schedules_equipment ON maintenance_schedules(equipment_id);
CREATE INDEX IF NOT EXISTS idx_schedules_next_due ON maintenance_schedules(next_due);

-- Parts indexes
CREATE INDEX IF NOT EXISTS idx_parts_organization ON parts_inventory(organization_id);
CREATE INDEX IF NOT EXISTS idx_parts_number ON parts_inventory(part_number);
CREATE INDEX IF NOT EXISTS idx_parts_low_stock ON parts_inventory(quantity_in_stock, minimum_stock_level);

-- Notifications indexes
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_unread ON notifications(user_id, is_read);

-- Audit logs indexes
CREATE INDEX IF NOT EXISTS idx_audit_organization ON audit_logs(organization_id);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);

-- Sessions indexes
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(is_active, expires_at);

-- Locations indexes
CREATE INDEX IF NOT EXISTS idx_locations_organization ON locations(organization_id);
CREATE INDEX IF NOT EXISTS idx_locations_parent ON locations(parent_location_id);

-- ============================================
-- SEED DATA: Default Roles
-- ============================================

INSERT OR IGNORE INTO roles (id, name, description, level) VALUES
    ('role_super_admin', 'super_admin', 'Full system access, manages all organizations', 1),
    ('role_admin', 'admin', 'Organization-level admin, manages users & settings', 2),
    ('role_manager', 'manager', 'Manages equipment, work orders, and technicians', 3),
    ('role_technician', 'technician', 'Performs maintenance, updates work orders, reports issues', 4);

-- ============================================
-- SEED DATA: Default Permissions
-- ============================================

INSERT OR IGNORE INTO permissions (id, name, resource, action, description) VALUES
    -- Organization permissions
    ('perm_org_create', 'organization:create', 'organization', 'create', 'Create new organizations'),
    ('perm_org_read', 'organization:read', 'organization', 'read', 'View organization details'),
    ('perm_org_update', 'organization:update', 'organization', 'update', 'Update organization settings'),
    ('perm_org_delete', 'organization:delete', 'organization', 'delete', 'Delete organizations'),
    
    -- User permissions
    ('perm_user_create', 'user:create', 'user', 'create', 'Create new users'),
    ('perm_user_read', 'user:read', 'user', 'read', 'View user profiles'),
    ('perm_user_update', 'user:update', 'user', 'update', 'Update user information'),
    ('perm_user_delete', 'user:delete', 'user', 'delete', 'Delete users'),
    ('perm_user_roles', 'user:manage_roles', 'user', 'manage', 'Assign/change user roles'),
    
    -- Equipment permissions
    ('perm_equip_create', 'equipment:create', 'equipment', 'create', 'Add new equipment'),
    ('perm_equip_read', 'equipment:read', 'equipment', 'read', 'View equipment details'),
    ('perm_equip_update', 'equipment:update', 'equipment', 'update', 'Update equipment information'),
    ('perm_equip_delete', 'equipment:delete', 'equipment', 'delete', 'Delete equipment'),
    ('perm_equip_report', 'equipment:report_issue', 'equipment', 'report', 'Report equipment issues'),
    
    -- Work Order permissions
    ('perm_wo_create', 'workorder:create', 'workorder', 'create', 'Create work orders'),
    ('perm_wo_read', 'workorder:read', 'workorder', 'read', 'View work orders'),
    ('perm_wo_update', 'workorder:update', 'workorder', 'update', 'Update work orders'),
    ('perm_wo_delete', 'workorder:delete', 'workorder', 'delete', 'Delete work orders'),
    ('perm_wo_assign', 'workorder:assign', 'workorder', 'assign', 'Assign work orders'),
    ('perm_wo_complete', 'workorder:complete', 'workorder', 'complete', 'Complete work orders'),
    
    -- Schedule permissions
    ('perm_sched_create', 'schedule:create', 'schedule', 'create', 'Create maintenance schedules'),
    ('perm_sched_read', 'schedule:read', 'schedule', 'read', 'View schedules'),
    ('perm_sched_update', 'schedule:update', 'schedule', 'update', 'Update schedules'),
    ('perm_sched_delete', 'schedule:delete', 'schedule', 'delete', 'Delete schedules'),
    
    -- Parts permissions
    ('perm_parts_create', 'parts:create', 'parts', 'create', 'Add new parts'),
    ('perm_parts_read', 'parts:read', 'parts', 'read', 'View parts inventory'),
    ('perm_parts_update', 'parts:update', 'parts', 'update', 'Update parts information'),
    ('perm_parts_delete', 'parts:delete', 'parts', 'delete', 'Delete parts'),
    ('perm_parts_use', 'parts:use', 'parts', 'use', 'Use parts from inventory'),
    
    -- Report permissions
    ('perm_report_create', 'report:create', 'report', 'create', 'Create reports'),
    ('perm_report_read', 'report:read', 'report', 'read', 'View reports'),
    ('perm_report_update', 'report:update', 'report', 'update', 'Update reports'),
    ('perm_report_delete', 'report:delete', 'report', 'delete', 'Delete reports'),
    ('perm_report_export', 'report:export', 'report', 'export', 'Export reports'),
    
    -- Admin permissions
    ('perm_settings', 'settings:manage', 'settings', 'manage', 'Manage organization settings'),
    ('perm_audit', 'audit:read', 'audit', 'read', 'View audit logs'),
    ('perm_notify', 'notification:manage', 'notification', 'manage', 'Manage notification settings');

-- ============================================
-- SEED DATA: Role-Permission Mappings
-- ============================================

-- Super Admin gets all permissions (using wildcard in code)
INSERT OR IGNORE INTO role_permissions (id, role_id, permission_id) 
SELECT 'rp_sa_' || id, 'role_super_admin', id FROM permissions;

-- Admin permissions
INSERT OR IGNORE INTO role_permissions (id, role_id, permission_id) VALUES
    ('rp_admin_org_read', 'role_admin', 'perm_org_read'),
    ('rp_admin_org_update', 'role_admin', 'perm_org_update'),
    ('rp_admin_user_create', 'role_admin', 'perm_user_create'),
    ('rp_admin_user_read', 'role_admin', 'perm_user_read'),
    ('rp_admin_user_update', 'role_admin', 'perm_user_update'),
    ('rp_admin_user_delete', 'role_admin', 'perm_user_delete'),
    ('rp_admin_user_roles', 'role_admin', 'perm_user_roles'),
    ('rp_admin_equip_create', 'role_admin', 'perm_equip_create'),
    ('rp_admin_equip_read', 'role_admin', 'perm_equip_read'),
    ('rp_admin_equip_update', 'role_admin', 'perm_equip_update'),
    ('rp_admin_equip_delete', 'role_admin', 'perm_equip_delete'),
    ('rp_admin_equip_report', 'role_admin', 'perm_equip_report'),
    ('rp_admin_wo_create', 'role_admin', 'perm_wo_create'),
    ('rp_admin_wo_read', 'role_admin', 'perm_wo_read'),
    ('rp_admin_wo_update', 'role_admin', 'perm_wo_update'),
    ('rp_admin_wo_delete', 'role_admin', 'perm_wo_delete'),
    ('rp_admin_wo_assign', 'role_admin', 'perm_wo_assign'),
    ('rp_admin_wo_complete', 'role_admin', 'perm_wo_complete'),
    ('rp_admin_sched_create', 'role_admin', 'perm_sched_create'),
    ('rp_admin_sched_read', 'role_admin', 'perm_sched_read'),
    ('rp_admin_sched_update', 'role_admin', 'perm_sched_update'),
    ('rp_admin_sched_delete', 'role_admin', 'perm_sched_delete'),
    ('rp_admin_parts_create', 'role_admin', 'perm_parts_create'),
    ('rp_admin_parts_read', 'role_admin', 'perm_parts_read'),
    ('rp_admin_parts_update', 'role_admin', 'perm_parts_update'),
    ('rp_admin_parts_delete', 'role_admin', 'perm_parts_delete'),
    ('rp_admin_parts_use', 'role_admin', 'perm_parts_use'),
    ('rp_admin_report_all', 'role_admin', 'perm_report_create'),
    ('rp_admin_report_read', 'role_admin', 'perm_report_read'),
    ('rp_admin_report_export', 'role_admin', 'perm_report_export'),
    ('rp_admin_settings', 'role_admin', 'perm_settings'),
    ('rp_admin_audit', 'role_admin', 'perm_audit');

-- Manager permissions
INSERT OR IGNORE INTO role_permissions (id, role_id, permission_id) VALUES
    ('rp_mgr_user_read', 'role_manager', 'perm_user_read'),
    ('rp_mgr_equip_create', 'role_manager', 'perm_equip_create'),
    ('rp_mgr_equip_read', 'role_manager', 'perm_equip_read'),
    ('rp_mgr_equip_update', 'role_manager', 'perm_equip_update'),
    ('rp_mgr_equip_delete', 'role_manager', 'perm_equip_delete'),
    ('rp_mgr_equip_report', 'role_manager', 'perm_equip_report'),
    ('rp_mgr_wo_create', 'role_manager', 'perm_wo_create'),
    ('rp_mgr_wo_read', 'role_manager', 'perm_wo_read'),
    ('rp_mgr_wo_update', 'role_manager', 'perm_wo_update'),
    ('rp_mgr_wo_delete', 'role_manager', 'perm_wo_delete'),
    ('rp_mgr_wo_assign', 'role_manager', 'perm_wo_assign'),
    ('rp_mgr_wo_complete', 'role_manager', 'perm_wo_complete'),
    ('rp_mgr_sched_create', 'role_manager', 'perm_sched_create'),
    ('rp_mgr_sched_read', 'role_manager', 'perm_sched_read'),
    ('rp_mgr_sched_update', 'role_manager', 'perm_sched_update'),
    ('rp_mgr_sched_delete', 'role_manager', 'perm_sched_delete'),
    ('rp_mgr_parts_create', 'role_manager', 'perm_parts_create'),
    ('rp_mgr_parts_read', 'role_manager', 'perm_parts_read'),
    ('rp_mgr_parts_update', 'role_manager', 'perm_parts_update'),
    ('rp_mgr_parts_delete', 'role_manager', 'perm_parts_delete'),
    ('rp_mgr_parts_use', 'role_manager', 'perm_parts_use'),
    ('rp_mgr_report_create', 'role_manager', 'perm_report_create'),
    ('rp_mgr_report_read', 'role_manager', 'perm_report_read'),
    ('rp_mgr_report_export', 'role_manager', 'perm_report_export');

-- Technician permissions (enhanced - can create work orders, report issues, view reports)
INSERT OR IGNORE INTO role_permissions (id, role_id, permission_id) VALUES
    ('rp_tech_equip_read', 'role_technician', 'perm_equip_read'),
    ('rp_tech_equip_update', 'role_technician', 'perm_equip_update'),
    ('rp_tech_equip_report', 'role_technician', 'perm_equip_report'),
    ('rp_tech_wo_create', 'role_technician', 'perm_wo_create'),
    ('rp_tech_wo_read', 'role_technician', 'perm_wo_read'),
    ('rp_tech_wo_update', 'role_technician', 'perm_wo_update'),
    ('rp_tech_wo_complete', 'role_technician', 'perm_wo_complete'),
    ('rp_tech_sched_read', 'role_technician', 'perm_sched_read'),
    ('rp_tech_parts_read', 'role_technician', 'perm_parts_read'),
    ('rp_tech_parts_use', 'role_technician', 'perm_parts_use'),
    ('rp_tech_report_read', 'role_technician', 'perm_report_read');

