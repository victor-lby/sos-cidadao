// MongoDB initialization script for development
db = db.getSiblingDB('sos_cidadao_dev');

// Create collections with validation
db.createCollection('organizations', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['name', 'slug', 'createdAt', 'updatedAt', 'createdBy', 'updatedBy', 'schemaVersion'],
      properties: {
        name: { bsonType: 'string', minLength: 1, maxLength: 200 },
        slug: { bsonType: 'string', pattern: '^[a-z0-9-]+$' },
        createdAt: { bsonType: 'date' },
        updatedAt: { bsonType: 'date' },
        deletedAt: { bsonType: ['date', 'null'] },
        createdBy: { bsonType: 'string' },
        updatedBy: { bsonType: 'string' },
        schemaVersion: { bsonType: 'int', minimum: 1 }
      }
    }
  }
});

db.createCollection('users', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['organizationId', 'email', 'name', 'passwordHash', 'roles', 'createdAt', 'updatedAt', 'createdBy', 'updatedBy', 'schemaVersion'],
      properties: {
        organizationId: { bsonType: 'objectId' },
        email: { bsonType: 'string', pattern: '^[^@]+@[^@]+\.[^@]+$' },
        name: { bsonType: 'string', minLength: 1, maxLength: 200 },
        passwordHash: { bsonType: 'string' },
        roles: { bsonType: 'array', items: { bsonType: 'objectId' } },
        createdAt: { bsonType: 'date' },
        updatedAt: { bsonType: 'date' },
        deletedAt: { bsonType: ['date', 'null'] },
        createdBy: { bsonType: 'string' },
        updatedBy: { bsonType: 'string' },
        schemaVersion: { bsonType: 'int', minimum: 1 }
      }
    }
  }
});

db.createCollection('notifications', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['organizationId', 'title', 'body', 'severity', 'origin', 'originalPayload', 'targets', 'categories', 'status', 'createdAt', 'updatedAt', 'createdBy', 'updatedBy', 'schemaVersion'],
      properties: {
        organizationId: { bsonType: 'objectId' },
        title: { bsonType: 'string', minLength: 1, maxLength: 200 },
        body: { bsonType: 'string', minLength: 1, maxLength: 2000 },
        severity: { bsonType: 'int', minimum: 0, maximum: 5 },
        origin: { bsonType: 'string' },
        originalPayload: { bsonType: 'object' },
        baseTarget: { bsonType: ['objectId', 'null'] },
        targets: { bsonType: 'array', items: { bsonType: 'objectId' } },
        categories: { bsonType: 'array', items: { bsonType: 'objectId' } },
        status: { enum: ['received', 'approved', 'denied', 'dispatched'] },
        denialReason: { bsonType: ['string', 'null'] },
        createdAt: { bsonType: 'date' },
        updatedAt: { bsonType: 'date' },
        deletedAt: { bsonType: ['date', 'null'] },
        createdBy: { bsonType: 'string' },
        updatedBy: { bsonType: 'string' },
        schemaVersion: { bsonType: 'int', minimum: 1 }
      }
    }
  }
});

db.createCollection('audit_logs', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['timestamp', 'userId', 'organizationId', 'entity', 'entityId', 'action', 'schemaVersion'],
      properties: {
        timestamp: { bsonType: 'date' },
        userId: { bsonType: 'objectId' },
        organizationId: { bsonType: 'objectId' },
        entity: { bsonType: 'string' },
        entityId: { bsonType: 'string' },
        action: { bsonType: 'string' },
        before: { bsonType: ['object', 'null'] },
        after: { bsonType: ['object', 'null'] },
        ipAddress: { bsonType: 'string' },
        userAgent: { bsonType: 'string' },
        traceId: { bsonType: 'string' },
        schemaVersion: { bsonType: 'int', minimum: 1 }
      }
    }
  }
});

// Create indexes for performance
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

print('MongoDB development database initialized successfully');