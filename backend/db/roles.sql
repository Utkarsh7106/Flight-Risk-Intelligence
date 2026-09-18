-- Run once per database, before the first `alembic upgrade`. Creates the two
-- Postgres roles the RLS design in ARCHITECTURE.md depends on:
--
--   fri_migrator  — owns the tables, runs migrations. Owners bypass Row
--                   Level Security by default, which is exactly what a
--                   migration/admin role needs.
--   fri_app       — the role the FastAPI app connects as at runtime.
--                   NOBYPASSRLS and not the table owner, so the RLS
--                   policies created in migration 5c6bf1a73a67 actually
--                   apply to it. Object-level GRANTs are issued by that
--                   migration, not here.
--
-- Change the passwords below before using this anywhere but local dev, and
-- point DATABASE_URL / MIGRATIONS_DATABASE_URL (see .env.example) at the
-- matching role.

CREATE ROLE fri_migrator LOGIN PASSWORD 'fri_migrator_dev_pw';
CREATE ROLE fri_app LOGIN PASSWORD 'fri_app_dev_pw' NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;

-- Run as a superuser, then connect as that superuser to the target database
-- (e.g. `\c fri_dev`) before continuing:
-- ALTER DATABASE fri_dev OWNER TO fri_migrator;
-- GRANT ALL ON SCHEMA public TO fri_migrator;
-- GRANT USAGE ON SCHEMA public TO fri_app;
