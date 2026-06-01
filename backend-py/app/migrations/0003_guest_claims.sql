-- Guest data claim tokens and idempotent migration records.

CREATE TABLE IF NOT EXISTS guest_claim_tokens (
    token_hash TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id),
    guest_id TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_guest_claim_tokens_guest_id ON guest_claim_tokens(tenant_id, guest_id);

CREATE TABLE IF NOT EXISTS guest_claims (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id),
    guest_id TEXT NOT NULL,
    user_id TEXT NOT NULL REFERENCES users(id),
    status TEXT NOT NULL,
    claim_token_hash TEXT NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    archive_path TEXT,
    UNIQUE (tenant_id, guest_id)
);

CREATE INDEX IF NOT EXISTS idx_guest_claims_user_id ON guest_claims(tenant_id, user_id);
