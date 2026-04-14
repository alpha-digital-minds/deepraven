-- DeepRaven multi-tenant schema
-- Run this in the Supabase SQL editor or via the Supabase CLI.

-- ── Accounts ─────────────────────────────────────────────────────────────────
-- One account per Supabase Auth user. Created automatically via trigger.
CREATE TABLE IF NOT EXISTS accounts (
  id          uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  name        text NOT NULL,
  created_at  timestamptz DEFAULT now()
);

-- ── Projects ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS projects (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id  uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  name        text NOT NULL,
  description text,
  created_at  timestamptz DEFAULT now(),
  updated_at  timestamptz DEFAULT now()
);

-- ── API Keys ─────────────────────────────────────────────────────────────────
-- Raw key is never stored — only its SHA-256 hex digest.
CREATE TABLE IF NOT EXISTS api_keys (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id   uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name         text NOT NULL,
  key_hash     text NOT NULL UNIQUE,
  created_at   timestamptz DEFAULT now(),
  last_used_at timestamptz,
  revoked_at   timestamptz
);

-- ── Contacts ─────────────────────────────────────────────────────────────────
-- "Contacts" are the end-users tracked by the customer's sales agents.
-- external_id is the caller's own identifier (e.g. CRM ID, email).
CREATE TABLE IF NOT EXISTS contacts (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id  uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  external_id text NOT NULL,
  created_at  timestamptz DEFAULT now(),
  UNIQUE(project_id, external_id)
);

-- ── Profiles ─────────────────────────────────────────────────────────────────
-- One profile per contact. data is the full UserProfile JSON (without user_id).
CREATE TABLE IF NOT EXISTS profiles (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id  uuid NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  project_id  uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  data        jsonb NOT NULL DEFAULT '{}',
  created_at  timestamptz DEFAULT now(),
  updated_at  timestamptz DEFAULT now(),
  UNIQUE(contact_id)
);

-- ── Conversations ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS conversations (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_id  uuid NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  project_id  uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  messages    jsonb NOT NULL,
  metadata    jsonb,
  timestamp   timestamptz DEFAULT now(),
  processed   boolean NOT NULL DEFAULT false
);

CREATE INDEX IF NOT EXISTS idx_conversations_contact_processed
  ON conversations(contact_id, processed);

-- ── Row-Level Security ────────────────────────────────────────────────────────
ALTER TABLE accounts      ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects      ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys      ENABLE ROW LEVEL SECURITY;
ALTER TABLE contacts      ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles      ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

-- accounts: each user sees only their own row
CREATE POLICY accounts_self ON accounts
  FOR ALL USING (id = auth.uid());

-- projects: account owner has full access
CREATE POLICY projects_owner ON projects
  FOR ALL USING (account_id = auth.uid());

-- api_keys: owner of the project has full access
CREATE POLICY api_keys_owner ON api_keys
  FOR ALL USING (
    project_id IN (SELECT id FROM projects WHERE account_id = auth.uid())
  );

-- contacts: owner of the project has full access
CREATE POLICY contacts_owner ON contacts
  FOR ALL USING (
    project_id IN (SELECT id FROM projects WHERE account_id = auth.uid())
  );

-- profiles: owner of the project has full access
CREATE POLICY profiles_owner ON profiles
  FOR ALL USING (
    project_id IN (SELECT id FROM projects WHERE account_id = auth.uid())
  );

-- conversations: owner of the project has full access
CREATE POLICY conversations_owner ON conversations
  FOR ALL USING (
    project_id IN (SELECT id FROM projects WHERE account_id = auth.uid())
  );

-- ── Auto-create account row on sign-up ───────────────────────────────────────
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO accounts(id, name)
  VALUES (NEW.id, COALESCE(NEW.raw_user_meta_data->>'name', NEW.email));
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE handle_new_user();

-- ── updated_at auto-bump for projects ────────────────────────────────────────
CREATE OR REPLACE FUNCTION touch_updated_at()
RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS projects_updated_at ON projects;
CREATE TRIGGER projects_updated_at
  BEFORE UPDATE ON projects
  FOR EACH ROW EXECUTE PROCEDURE touch_updated_at();

DROP TRIGGER IF EXISTS profiles_updated_at ON profiles;
CREATE TRIGGER profiles_updated_at
  BEFORE UPDATE ON profiles
  FOR EACH ROW EXECUTE PROCEDURE touch_updated_at();
