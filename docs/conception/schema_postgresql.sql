-- =========================================================================
-- FraudGuard — Script de création de la base de données PostgreSQL
-- Version 1.0 — Aligné avec le CDC v2.1 et les diagrammes UML corrigés
-- =========================================================================

-- Extension pour UUID si besoin de identifiants externes non séquentiels
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =========================================================================
-- TABLE: users
-- Rôle: Administrateur, Analyste Fraude, Agent Financier
-- =========================================================================
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    first_name      VARCHAR(100)    NOT NULL,
    last_name       VARCHAR(100)    NOT NULL,
    email           VARCHAR(255)    NOT NULL UNIQUE,
    password        VARCHAR(255)    NOT NULL,
    role            VARCHAR(20)     NOT NULL
                        CHECK (role IN ('admin', 'analyst', 'agent')),
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    date_joined     TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    last_login      TIMESTAMPTZ
);

CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_email ON users(email);

-- =========================================================================
-- TABLE: ml_models
-- Suivi des modèles ML déployés (CDC 5.3 / 5.5)
-- =========================================================================
CREATE TABLE ml_models (
    id              SERIAL PRIMARY KEY,
    version         VARCHAR(50)     NOT NULL UNIQUE,
    algorithm       VARCHAR(50)     NOT NULL
                        CHECK (algorithm IN ('logistic_regression', 'random_forest', 'xgboost')),
    precision_score FLOAT           CHECK (precision_score BETWEEN 0 AND 1),
    recall_score    FLOAT           CHECK (recall_score BETWEEN 0 AND 1),
    f1_score        FLOAT           CHECK (f1_score BETWEEN 0 AND 1),
    auc_roc         FLOAT           CHECK (auc_roc BETWEEN 0 AND 1),
    trained_at      TIMESTAMPTZ     NOT NULL,
    is_active       BOOLEAN         NOT NULL DEFAULT FALSE,
    artifact_path   VARCHAR(255)    NOT NULL
);

-- Un seul modèle actif à la fois (contrainte applicative + index partiel)
CREATE UNIQUE INDEX idx_ml_models_single_active
    ON ml_models(is_active)
    WHERE is_active = TRUE;

-- =========================================================================
-- TABLE: transactions
-- CDC 5.2 — Gestion des transactions
-- =========================================================================
CREATE TABLE transactions (
    id                  SERIAL PRIMARY KEY,
    transaction_id      VARCHAR(50)     NOT NULL UNIQUE,
    amount              NUMERIC(12, 2)  NOT NULL CHECK (amount > 0),
    merchant            VARCHAR(255),
    device              VARCHAR(100),
    location            VARCHAR(255),
    channel             VARCHAR(30)
                            CHECK (channel IN ('card', 'mobile_money', 'transfer', 'online')),
    "timestamp"         TIMESTAMPTZ     NOT NULL,
    status              VARCHAR(20)     NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'legitimate', 'fraudulent', 'under_review')),
    created_by_id       INTEGER         REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_transactions_status ON transactions(status);
CREATE INDEX idx_transactions_timestamp ON transactions("timestamp");
CREATE INDEX idx_transactions_channel ON transactions(channel);
CREATE INDEX idx_transactions_created_by ON transactions(created_by_id);

-- =========================================================================
-- TABLE: predictions
-- CDC 5.3 — Scoring automatique des transactions
-- =========================================================================
CREATE TABLE predictions (
    id                  SERIAL PRIMARY KEY,
    transaction_id      INTEGER         NOT NULL UNIQUE
                            REFERENCES transactions(id) ON DELETE CASCADE,
    ml_model_id         INTEGER         NOT NULL
                            REFERENCES ml_models(id) ON DELETE RESTRICT,
    fraud_probability   FLOAT           NOT NULL CHECK (fraud_probability BETWEEN 0 AND 1),
    prediction          BOOLEAN         NOT NULL,
    prediction_date     TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_predictions_fraud_probability ON predictions(fraud_probability);
CREATE INDEX idx_predictions_ml_model ON predictions(ml_model_id);

-- =========================================================================
-- TABLE: alerts
-- CDC 5.3 / 5.4 — Seuils configurables déclenchant une alerte
-- =========================================================================
CREATE TABLE alerts (
    id                  SERIAL PRIMARY KEY,
    prediction_id       INTEGER         NOT NULL UNIQUE
                            REFERENCES predictions(id) ON DELETE CASCADE,
    assigned_to_id      INTEGER         REFERENCES users(id) ON DELETE SET NULL,
    status              VARCHAR(20)     NOT NULL DEFAULT 'open'
                            CHECK (status IN ('open', 'confirmed', 'rejected', 'resolved')),
    severity            VARCHAR(10)     NOT NULL DEFAULT 'medium'
                            CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    comment             TEXT,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    resolved_at         TIMESTAMPTZ
);

CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_alerts_assigned_to ON alerts(assigned_to_id);

-- =========================================================================
-- TABLE: reports
-- CDC 5.5 — Génération de rapports (PDF/CSV)
-- =========================================================================
CREATE TABLE reports (
    id                  SERIAL PRIMARY KEY,
    title               VARCHAR(255)    NOT NULL,
    type                VARCHAR(10)     NOT NULL CHECK (type IN ('pdf', 'csv')),
    generated_by_id     INTEGER         REFERENCES users(id) ON DELETE SET NULL,
    period_start        DATE,
    period_end          DATE,
    file_path           VARCHAR(255),
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_reports_generated_by ON reports(generated_by_id);
CREATE INDEX idx_reports_created_at ON reports(created_at);

-- =========================================================================
-- TABLE: audit_logs
-- CDC section 6 — Conformité, logs d'audit des accès aux données sensibles
-- =========================================================================
CREATE TABLE audit_logs (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER         REFERENCES users(id) ON DELETE SET NULL,
    action              VARCHAR(100)    NOT NULL,
    ip_address          VARCHAR(45),
    details             JSONB,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);

-- =========================================================================
-- Fin du script
-- =========================================================================
