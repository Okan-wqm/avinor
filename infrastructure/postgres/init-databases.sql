-- =============================================================================
-- Initialize Databases and Users for All Microservices
-- =============================================================================

-- Create extension for UUID support
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- =============================================================================
-- REPLICATION USER
-- =============================================================================
CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD 'replicator_secure_password_change_me';

-- =============================================================================
-- SERVICE DATABASES AND USERS
-- =============================================================================

-- User Service Database
CREATE DATABASE user_db
    WITH ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;

CREATE USER user_service WITH ENCRYPTED PASSWORD 'user_service_password_change_me';
GRANT ALL PRIVILEGES ON DATABASE user_db TO user_service;
ALTER DATABASE user_db OWNER TO user_service;

-- Organization Service Database
CREATE DATABASE org_db
    WITH ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;

CREATE USER org_service WITH ENCRYPTED PASSWORD 'org_service_password_change_me';
GRANT ALL PRIVILEGES ON DATABASE org_db TO org_service;
ALTER DATABASE org_db OWNER TO org_service;

-- Aircraft Service Database
CREATE DATABASE aircraft_db
    WITH ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;

CREATE USER aircraft_service WITH ENCRYPTED PASSWORD 'aircraft_service_password_change_me';
GRANT ALL PRIVILEGES ON DATABASE aircraft_db TO aircraft_service;
ALTER DATABASE aircraft_db OWNER TO aircraft_service;

-- Maintenance Service Database
CREATE DATABASE maintenance_db
    WITH ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;

CREATE USER maintenance_service WITH ENCRYPTED PASSWORD 'maintenance_service_password_change_me';
GRANT ALL PRIVILEGES ON DATABASE maintenance_db TO maintenance_service;
ALTER DATABASE maintenance_db OWNER TO maintenance_service;

-- Booking Service Database
CREATE DATABASE booking_db
    WITH ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;

CREATE USER booking_service WITH ENCRYPTED PASSWORD 'booking_service_password_change_me';
GRANT ALL PRIVILEGES ON DATABASE booking_db TO booking_service;
ALTER DATABASE booking_db OWNER TO booking_service;

-- Flight Service Database
CREATE DATABASE flight_db
    WITH ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;

CREATE USER flight_service WITH ENCRYPTED PASSWORD 'flight_service_password_change_me';
GRANT ALL PRIVILEGES ON DATABASE flight_db TO flight_service;
ALTER DATABASE flight_db OWNER TO flight_service;

-- Training Service Database
CREATE DATABASE training_db
    WITH ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;

CREATE USER training_service WITH ENCRYPTED PASSWORD 'training_service_password_change_me';
GRANT ALL PRIVILEGES ON DATABASE training_db TO training_service;
ALTER DATABASE training_db OWNER TO training_service;

-- Theory Service Database
CREATE DATABASE theory_db
    WITH ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;

CREATE USER theory_service WITH ENCRYPTED PASSWORD 'theory_service_password_change_me';
GRANT ALL PRIVILEGES ON DATABASE theory_db TO theory_service;
ALTER DATABASE theory_db OWNER TO theory_service;

-- Certificate Service Database
CREATE DATABASE cert_db
    WITH ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;

CREATE USER cert_service WITH ENCRYPTED PASSWORD 'cert_service_password_change_me';
GRANT ALL PRIVILEGES ON DATABASE cert_db TO cert_service;
ALTER DATABASE cert_db OWNER TO cert_service;

-- Finance Service Database
CREATE DATABASE finance_db
    WITH ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;

CREATE USER finance_service WITH ENCRYPTED PASSWORD 'finance_service_password_change_me';
GRANT ALL PRIVILEGES ON DATABASE finance_db TO finance_service;
ALTER DATABASE finance_db OWNER TO finance_service;

-- Document Service Database
CREATE DATABASE doc_db
    WITH ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;

CREATE USER doc_service WITH ENCRYPTED PASSWORD 'doc_service_password_change_me';
GRANT ALL PRIVILEGES ON DATABASE doc_db TO doc_service;
ALTER DATABASE doc_db OWNER TO doc_service;

-- Report Service Database
CREATE DATABASE report_db
    WITH ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;

CREATE USER report_service WITH ENCRYPTED PASSWORD 'report_service_password_change_me';
GRANT ALL PRIVILEGES ON DATABASE report_db TO report_service;
ALTER DATABASE report_db OWNER TO report_service;

-- Notification Service Database
CREATE DATABASE notif_db
    WITH ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;

CREATE USER notif_service WITH ENCRYPTED PASSWORD 'notif_service_password_change_me';
GRANT ALL PRIVILEGES ON DATABASE notif_db TO notif_service;
ALTER DATABASE notif_db OWNER TO notif_service;

-- =============================================================================
-- GRANT SCHEMA PERMISSIONS
-- =============================================================================

-- Function to grant schema permissions
CREATE OR REPLACE FUNCTION grant_schema_permissions(db_name TEXT, user_name TEXT)
RETURNS VOID AS $$
BEGIN
    EXECUTE format('GRANT ALL ON SCHEMA public TO %I', user_name);
    EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO %I', user_name);
    EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO %I', user_name);
    EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO %I', user_name);
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- ENABLE EXTENSIONS FOR EACH DATABASE
-- =============================================================================

\c user_db
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

\c org_db
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

\c aircraft_db
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

\c maintenance_db
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

\c booking_db
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "btree_gist";

\c flight_db
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

\c training_db
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

\c theory_db
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

\c cert_db
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

\c finance_db
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

\c doc_db
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

\c report_db
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "tablefunc";

\c notif_db
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Return to default database
\c postgres

SELECT 'All databases and users created successfully!' as status;
