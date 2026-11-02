-- ==============================================================================
-- VOIDONYX & VOIDPANEL — DOVECOT & POSTFIX DATABASE SCHEMA AND QUERIES
-- ==============================================================================

-- 1. Create Tables for Virtual Mail System
CREATE TABLE IF NOT EXISTS virtual_domains (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    is_verified BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS virtual_mailboxes (
    id SERIAL PRIMARY KEY,
    domain_id INT REFERENCES virtual_domains(id) ON DELETE CASCADE,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL, -- e.g. {SHA512-CRYPT}$6$...
    quota_mb INT DEFAULT 5120,
    used_mb INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS virtual_aliases (
    id SERIAL PRIMARY KEY,
    source_email VARCHAR(255) NOT NULL UNIQUE,
    destination_email VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- 2. DOVECOT CONFIGURATION QUERIES (/etc/dovecot/dovecot-sql.conf.ext)
-- ==============================================================================

-- Driver: pgsql or mysql
-- connect = host=127.0.0.1 dbname=voidmail user=voidmail_user password=secret_password

-- Password query for Dovecot IMAP/POP3 authentication:
-- password_query = SELECT email as user, password_hash as password FROM virtual_mailboxes WHERE email = '%u' AND is_active = true;

-- User query for Dovecot maildir delivery:
-- user_query = SELECT concat('/var/vmail/', domain.name, '/', username, '/') as home, 5000 as uid, 5000 as gid, concat('*:bytes=', quota_mb, 'M') as quota_rule FROM virtual_mailboxes JOIN virtual_domains as domain ON domain.id = virtual_mailboxes.domain_id WHERE email = '%u' AND is_active = true;


-- ==============================================================================
-- 3. POSTFIX CONFIGURATION QUERIES (/etc/postfix/virtual-*.cf)
-- ==============================================================================

-- /etc/postfix/virtual_mailbox_domains.cf:
-- query = SELECT 1 FROM virtual_domains WHERE name='%s' AND is_verified = true;

-- /etc/postfix/virtual_mailbox_maps.cf:
-- query = SELECT 1 FROM virtual_mailboxes WHERE email='%s' AND is_active = true;

-- /etc/postfix/virtual_alias_maps.cf:
-- query = SELECT destination_email FROM virtual_aliases WHERE source_email='%s' AND is_active = true;
