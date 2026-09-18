"""row level security, sync triggers, app role grants

Revision ID: 5c6bf1a73a67
Revises: d1049acb7f8f
Create Date: 2026-09-18 09:47:48.763433

Prerequisite: db/roles.sql must have been run against this database first
(creates the fri_app runtime role these GRANTs target). See ARCHITECTURE.md.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '5c6bf1a73a67'
down_revision: Union[str, None] = 'd1049acb7f8f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Triggers -----------------------------------------------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION sync_employee_business_unit() RETURNS trigger AS $$
        BEGIN
            NEW.business_unit_id := (
                SELECT business_unit_id FROM department WHERE id = NEW.department_id
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_employee_sync_business_unit
        BEFORE INSERT OR UPDATE OF department_id ON employee
        FOR EACH ROW
        EXECUTE FUNCTION sync_employee_business_unit();
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION mark_employee_separated() RETURNS trigger AS $$
        BEGIN
            UPDATE employee SET employment_status = 'separated' WHERE id = NEW.employee_id;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_departure_event_mark_separated
        AFTER INSERT ON departure_event
        FOR EACH ROW
        EXECUTE FUNCTION mark_employee_separated();
        """
    )

    # --- Row Level Security --------------------------------------------
    # Second, independent layer on top of the app-level role-scoping
    # dependency (app/security/deps.py). Policies read session variables
    # set per-request via set_config(..., true) (SET LOCAL semantics). If
    # those variables are unset — e.g. a raw psql session, or any bug that
    # skips the app-level dependency — current_setting(..., true) returns
    # NULL and every policy below evaluates false: access fails closed.
    op.execute("ALTER TABLE employee ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY employee_hr_full_access ON employee
        FOR ALL
        USING (current_setting('app.current_role', true) = 'hr')
        WITH CHECK (current_setting('app.current_role', true) = 'hr')
        """
    )
    op.execute(
        """
        CREATE POLICY employee_bu_head_scoped ON employee
        FOR ALL
        USING (
            current_setting('app.current_role', true) = 'bu_head'
            AND business_unit_id::text = current_setting('app.current_bu_id', true)
        )
        WITH CHECK (
            current_setting('app.current_role', true) = 'bu_head'
            AND business_unit_id::text = current_setting('app.current_bu_id', true)
        )
        """
    )

    op.execute("ALTER TABLE departure_event ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY departure_event_hr_full_access ON departure_event
        FOR ALL
        USING (current_setting('app.current_role', true) = 'hr')
        WITH CHECK (current_setting('app.current_role', true) = 'hr')
        """
    )
    op.execute(
        """
        CREATE POLICY departure_event_bu_head_scoped ON departure_event
        FOR ALL
        USING (
            current_setting('app.current_role', true) = 'bu_head'
            AND business_unit_id::text = current_setting('app.current_bu_id', true)
        )
        WITH CHECK (
            current_setting('app.current_role', true) = 'bu_head'
            AND business_unit_id::text = current_setting('app.current_bu_id', true)
        )
        """
    )

    # --- Runtime role grants --------------------------------------------
    # fri_app is a NOBYPASSRLS, non-owner role (created by db/roles.sql), so
    # RLS above actually applies to it — the table owner (fri_migrator, used
    # only for migrations) would otherwise bypass RLS entirely.
    # business_unit/department are non-sensitive reference data: both roles
    # read them freely, writes are gated at the app layer (HR only), not RLS.
    # app_user carries no RLS — it is only ever read internally by the auth
    # dependency, never returned to a bu_head as directory data.
    op.execute("GRANT USAGE ON SCHEMA public TO fri_app")
    op.execute("GRANT SELECT ON business_unit, department TO fri_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON employee, app_user, departure_event TO fri_app")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO fri_app")


def downgrade() -> None:
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM fri_app")
    op.execute("REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM fri_app")
    op.execute("REVOKE USAGE ON SCHEMA public FROM fri_app")

    op.execute("DROP POLICY IF EXISTS departure_event_bu_head_scoped ON departure_event")
    op.execute("DROP POLICY IF EXISTS departure_event_hr_full_access ON departure_event")
    op.execute("ALTER TABLE departure_event DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS employee_bu_head_scoped ON employee")
    op.execute("DROP POLICY IF EXISTS employee_hr_full_access ON employee")
    op.execute("ALTER TABLE employee DISABLE ROW LEVEL SECURITY")

    op.execute("DROP TRIGGER IF EXISTS trg_departure_event_mark_separated ON departure_event")
    op.execute("DROP FUNCTION IF EXISTS mark_employee_separated")

    op.execute("DROP TRIGGER IF EXISTS trg_employee_sync_business_unit ON employee")
    op.execute("DROP FUNCTION IF EXISTS sync_employee_business_unit")
