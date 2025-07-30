BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> d7911c4ffe4c

CREATE TABLE users (
    id SERIAL NOT NULL, 
    email VARCHAR(255) NOT NULL, 
    hashed_password VARCHAR(255) NOT NULL, 
    name VARCHAR(255), 
    is_active BOOLEAN, 
    email_verified BOOLEAN, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE INDEX ix_users_id ON users (id);

INSERT INTO alembic_version (version_num) VALUES ('d7911c4ffe4c') RETURNING alembic_version.version_num;

COMMIT;

