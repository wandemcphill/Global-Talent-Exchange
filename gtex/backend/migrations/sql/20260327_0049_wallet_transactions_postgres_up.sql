CREATE OR REPLACE FUNCTION wallet_enforce_double_entry_transaction()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    target_transaction_id text := NEW.transaction_id;
    entry_count integer;
    imbalance_count integer;
BEGIN
    SELECT COUNT(*)
    INTO entry_count
    FROM ledger_entries
    WHERE transaction_id = target_transaction_id;

    IF entry_count < 2 THEN
        RAISE EXCEPTION 'Transaction % must contain at least two ledger entries.', target_transaction_id
            USING ERRCODE = '23514';
    END IF;

    SELECT COUNT(*)
    INTO imbalance_count
    FROM (
        SELECT unit
        FROM ledger_entries
        WHERE transaction_id = target_transaction_id
        GROUP BY unit
        HAVING COALESCE(SUM(amount), 0) <> 0
    ) imbalances;

    IF imbalance_count > 0 THEN
        RAISE EXCEPTION 'Transaction % is not balanced across ledger units.', target_transaction_id
            USING ERRCODE = '23514';
    END IF;

    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_ledger_entries_double_entry ON ledger_entries;
CREATE CONSTRAINT TRIGGER trg_ledger_entries_double_entry
AFTER INSERT ON ledger_entries
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION wallet_enforce_double_entry_transaction();

CREATE OR REPLACE FUNCTION wallet_prevent_ledger_entry_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'Ledger entries are append-only and cannot be %.', lower(TG_OP)
        USING ERRCODE = '55000';
END;
$$;

DROP TRIGGER IF EXISTS trg_ledger_entries_append_only ON ledger_entries;
CREATE TRIGGER trg_ledger_entries_append_only
BEFORE UPDATE OR DELETE ON ledger_entries
FOR EACH ROW
EXECUTE FUNCTION wallet_prevent_ledger_entry_mutation();
