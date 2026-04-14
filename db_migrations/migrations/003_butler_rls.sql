-- Butler dashboard Row-Level Security
-- Run this in the Supabase SQL editor.
-- Ensures each customer account only sees its own tenants, contacts, and conversations.
-- Admins (app_role = 'admin' JWT claim) retain full access.

-- ── Helper: is the current user an admin? ─────────────────────────────────────
-- Avoids repeating the JWT check in every policy.
CREATE OR REPLACE FUNCTION is_admin()
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
  SELECT (auth.jwt() ->> 'app_role') = 'admin';
$$;

-- ── tenants ───────────────────────────────────────────────────────────────────
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;

-- Admins have full access
CREATE POLICY "tenants_admin_all" ON tenants
  FOR ALL
  USING (is_admin())
  WITH CHECK (is_admin());

-- Customers can read only their account's tenants
CREATE POLICY "tenants_customer_select" ON tenants
  FOR SELECT
  USING (
    account_id IN (
      SELECT account_id
      FROM customer_account_members
      WHERE user_id = auth.uid()
    )
  );

-- Customers can update/insert tenants for their own account
CREATE POLICY "tenants_customer_write" ON tenants
  FOR INSERT
  WITH CHECK (
    account_id IN (
      SELECT account_id
      FROM customer_account_members
      WHERE user_id = auth.uid()
    )
  );

CREATE POLICY "tenants_customer_update" ON tenants
  FOR UPDATE
  USING (
    account_id IN (
      SELECT account_id
      FROM customer_account_members
      WHERE user_id = auth.uid()
    )
  )
  WITH CHECK (
    account_id IN (
      SELECT account_id
      FROM customer_account_members
      WHERE user_id = auth.uid()
    )
  );

-- ── customer_accounts ─────────────────────────────────────────────────────────
ALTER TABLE customer_accounts ENABLE ROW LEVEL SECURITY;

-- Admins see all
CREATE POLICY "customer_accounts_admin_all" ON customer_accounts
  FOR ALL
  USING (is_admin())
  WITH CHECK (is_admin());

-- Customers see only their own account
CREATE POLICY "customer_accounts_owner_select" ON customer_accounts
  FOR SELECT
  USING (
    id IN (
      SELECT account_id
      FROM customer_account_members
      WHERE user_id = auth.uid()
    )
  );

-- ── customer_account_members ──────────────────────────────────────────────────
ALTER TABLE customer_account_members ENABLE ROW LEVEL SECURITY;

-- Admins see all
CREATE POLICY "cam_admin_all" ON customer_account_members
  FOR ALL
  USING (is_admin())
  WITH CHECK (is_admin());

-- Customers can insert their own membership row (accept-invite flow)
CREATE POLICY "cam_self_insert" ON customer_account_members
  FOR INSERT
  WITH CHECK (user_id = auth.uid());

-- Customers can read their own membership rows
CREATE POLICY "cam_self_select" ON customer_account_members
  FOR SELECT
  USING (user_id = auth.uid());

-- ── tenant_usage_stats ────────────────────────────────────────────────────────
-- Enable RLS only if this is a real table (skip if it's a view)
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_tables
    WHERE schemaname = 'public' AND tablename = 'tenant_usage_stats'
  ) THEN
    ALTER TABLE tenant_usage_stats ENABLE ROW LEVEL SECURITY;

    EXECUTE $p$
      CREATE POLICY "tstats_admin_all" ON tenant_usage_stats
        FOR ALL USING (is_admin()) WITH CHECK (is_admin());
    $p$;

    EXECUTE $p$
      CREATE POLICY "tstats_customer_select" ON tenant_usage_stats
        FOR SELECT
        USING (
          tenant_id IN (
            SELECT t.id FROM tenants t
            JOIN customer_account_members cam ON cam.account_id = t.account_id
            WHERE cam.user_id = auth.uid()
          )
        );
    $p$;
  END IF;
END;
$$;

-- ── butler_contacts ───────────────────────────────────────────────────────────
ALTER TABLE butler_contacts ENABLE ROW LEVEL SECURITY;

-- Admins see all
CREATE POLICY "butler_contacts_admin_all" ON butler_contacts
  FOR ALL
  USING (is_admin())
  WITH CHECK (is_admin());

-- Customers see contacts for their tenants only
CREATE POLICY "butler_contacts_customer_select" ON butler_contacts
  FOR SELECT
  USING (
    tenant_id IN (
      SELECT t.id FROM tenants t
      JOIN customer_account_members cam ON cam.account_id = t.account_id
      WHERE cam.user_id = auth.uid()
    )
  );

-- ── butler_conversations ──────────────────────────────────────────────────────
ALTER TABLE butler_conversations ENABLE ROW LEVEL SECURITY;

-- Admins see all
CREATE POLICY "butler_conversations_admin_all" ON butler_conversations
  FOR ALL
  USING (is_admin())
  WITH CHECK (is_admin());

-- Customers see conversations for their tenants only
CREATE POLICY "butler_conversations_customer_select" ON butler_conversations
  FOR SELECT
  USING (
    tenant_id IN (
      SELECT t.id FROM tenants t
      JOIN customer_account_members cam ON cam.account_id = t.account_id
      WHERE cam.user_id = auth.uid()
    )
  );

CREATE POLICY "butler_conversations_customer_update" ON butler_conversations
  FOR UPDATE
  USING (
    tenant_id IN (
      SELECT t.id FROM tenants t
      JOIN customer_account_members cam ON cam.account_id = t.account_id
      WHERE cam.user_id = auth.uid()
    )
  );

-- ── views: make them respect the caller's RLS (Postgres 15+) ─────────────────
-- If your Postgres version is < 15, drop and recreate the views with
-- a SECURITY INVOKER option or filter them by a function instead.
DO $$
DECLARE
  v text;
BEGIN
  FOREACH v IN ARRAY ARRAY['tenant_usage_stats', 'chatbot_usage_daily', 'chatbot_usage_monthly'] LOOP
    IF EXISTS (SELECT 1 FROM pg_views WHERE schemaname = 'public' AND viewname = v) THEN
      EXECUTE format('ALTER VIEW %I SET (security_invoker = true)', v);
    END IF;
  END LOOP;
END;
$$;
