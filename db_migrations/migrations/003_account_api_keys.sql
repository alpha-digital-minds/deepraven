-- Migration 003: account-level API keys
--
-- Allows service accounts (e.g. Butler Agent) to authenticate with DeepRaven
-- using a long-lived key scoped to an account rather than a single project.
-- Account keys use the prefix "dra_" and can perform any operation the account
-- owner can do via JWT: create/delete projects, create project keys, etc.
--
-- Key management (create / revoke) is still JWT-only to prevent bootstrap issues.

CREATE TABLE IF NOT EXISTS account_api_keys (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id   uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  name         text NOT NULL,
  key_hash     text NOT NULL UNIQUE,
  created_at   timestamptz DEFAULT now(),
  last_used_at timestamptz,
  revoked_at   timestamptz
);

CREATE INDEX IF NOT EXISTS idx_account_api_keys_hash       ON account_api_keys (key_hash);
CREATE INDEX IF NOT EXISTS idx_account_api_keys_account_id ON account_api_keys (account_id);
