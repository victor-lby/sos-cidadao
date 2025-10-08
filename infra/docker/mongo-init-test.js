// MongoDB initialization script for testing
db = db.getSiblingDB('sos_cidadao_test');

// Create the same collections as development but without strict validation for testing flexibility
db.createCollection('organizations');
db.createCollection('users');
db.createCollection('notifications');
db.createCollection('audit_logs');

// Create the same indexes for consistent performance testing
db.organizations.createIndex({ 'slug': 1 }, { unique: true });
db.organizations.createIndex({ 'deletedAt': 1 });

db.users.createIndex({ 'organizationId': 1, 'email': 1 }, { unique: true });
db.users.createIndex({ 'organizationId': 1, 'deletedAt': 1 });

db.notifications.createIndex({ 'organizationId': 1, 'status': 1, 'createdAt': -1 });
db.notifications.createIndex({ 'organizationId': 1, 'deletedAt': 1 });
db.notifications.createIndex({ 'organizationId': 1, 'severity': 1 });

db.audit_logs.createIndex({ 'organizationId': 1, 'timestamp': -1 });
db.audit_logs.createIndex({ 'organizationId': 1, 'userId': 1, 'timestamp': -1 });
db.audit_logs.createIndex({ 'organizationId': 1, 'entity': 1, 'timestamp': -1 });
db.audit_logs.createIndex({ 'traceId': 1 });

print('MongoDB test database initialized successfully');