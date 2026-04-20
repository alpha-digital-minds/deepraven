-- 004_account_config.sql
-- Account-level custom schema and generated extraction prompts

CREATE TABLE IF NOT EXISTS account_config (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id           uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  profile_schema       jsonb NOT NULL DEFAULT '{}',
  purpose_industry     text NOT NULL DEFAULT '',
  purpose_agent_type   text NOT NULL DEFAULT '',
  purpose_description  text NOT NULL DEFAULT '',
  prompt_extractor     text NOT NULL DEFAULT '',
  prompt_reviewer      text NOT NULL DEFAULT '',
  prompt_compressor    text NOT NULL DEFAULT '',
  created_at           timestamptz DEFAULT now(),
  updated_at           timestamptz DEFAULT now(),
  UNIQUE(account_id)
);

ALTER TABLE account_config ENABLE ROW LEVEL SECURITY;

CREATE POLICY account_config_owner ON account_config
  FOR ALL USING (account_id = auth.uid());

DROP TRIGGER IF EXISTS account_config_updated_at ON account_config;
CREATE TRIGGER account_config_updated_at
  BEFORE UPDATE ON account_config
  FOR EACH ROW EXECUTE PROCEDURE touch_updated_at();
