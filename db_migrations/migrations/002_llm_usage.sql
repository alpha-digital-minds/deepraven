-- ── LLM usage tracking ────────────────────────────────────────────────────────
-- One row per LLM extraction call; used for per-account / per-project billing insights.

CREATE TABLE IF NOT EXISTS llm_usage (
  id                uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
  account_id        uuid        NOT NULL REFERENCES accounts(id)  ON DELETE CASCADE,
  project_id        uuid        NOT NULL REFERENCES projects(id)  ON DELETE CASCADE,
  contact_id        uuid                 REFERENCES contacts(id)  ON DELETE SET NULL,
  prompt_tokens     int         NOT NULL DEFAULT 0,
  completion_tokens int         NOT NULL DEFAULT 0,
  total_tokens      int         NOT NULL DEFAULT 0,
  model             text,
  created_at        timestamptz DEFAULT now()
);

ALTER TABLE llm_usage ENABLE ROW LEVEL SECURITY;

CREATE POLICY "account_owns_usage" ON llm_usage
  FOR ALL USING (account_id = auth.uid());

CREATE INDEX idx_llm_usage_account ON llm_usage(account_id);
CREATE INDEX idx_llm_usage_project ON llm_usage(project_id);
CREATE INDEX idx_llm_usage_created ON llm_usage(created_at);

-- ── Analytics helper functions ─────────────────────────────────────────────────

-- Overview counts: projects, contacts, conversations, total tokens
CREATE OR REPLACE FUNCTION get_account_stats(p_account_id uuid)
RETURNS json
LANGUAGE sql
SECURITY DEFINER
AS $$
  SELECT json_build_object(
    'projects',      (SELECT count(*)::int  FROM projects                                                    WHERE account_id = p_account_id),
    'contacts',      (SELECT count(*)::int  FROM contacts c JOIN projects p ON c.project_id = p.id          WHERE p.account_id = p_account_id),
    'conversations', (SELECT count(*)::int  FROM conversations c JOIN projects p ON c.project_id = p.id     WHERE p.account_id = p_account_id),
    'total_tokens',  (SELECT COALESCE(sum(total_tokens), 0)::int FROM llm_usage                             WHERE account_id = p_account_id)
  );
$$;

-- Daily conversation counts for the last N days
CREATE OR REPLACE FUNCTION get_daily_conversations(p_account_id uuid, p_days int DEFAULT 30)
RETURNS TABLE(date date, count bigint)
LANGUAGE sql
SECURITY DEFINER
AS $$
  SELECT DATE(c.timestamp) AS date, COUNT(*) AS count
  FROM conversations c
  JOIN projects p ON c.project_id = p.id
  WHERE p.account_id = p_account_id
    AND c.timestamp >= (NOW() - (p_days || ' days')::interval)
  GROUP BY DATE(c.timestamp)
  ORDER BY date;
$$;

-- Per-project token usage rollup
CREATE OR REPLACE FUNCTION get_usage_by_project(p_account_id uuid)
RETURNS TABLE(
  project_id        uuid,
  project_name      text,
  total_tokens      bigint,
  prompt_tokens     bigint,
  completion_tokens bigint,
  calls             bigint
)
LANGUAGE sql
SECURITY DEFINER
AS $$
  SELECT
    p.id                                                   AS project_id,
    p.name                                                 AS project_name,
    COALESCE(SUM(u.total_tokens),      0)::bigint          AS total_tokens,
    COALESCE(SUM(u.prompt_tokens),     0)::bigint          AS prompt_tokens,
    COALESCE(SUM(u.completion_tokens), 0)::bigint          AS completion_tokens,
    COUNT(u.id)::bigint                                    AS calls
  FROM projects p
  LEFT JOIN llm_usage u ON u.project_id = p.id
  WHERE p.account_id = p_account_id
  GROUP BY p.id, p.name
  ORDER BY total_tokens DESC;
$$;
