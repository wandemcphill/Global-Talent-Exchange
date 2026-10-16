DROP TRIGGER IF EXISTS trg_ledger_entries_append_only ON ledger_entries;
DROP FUNCTION IF EXISTS wallet_prevent_ledger_entry_mutation();

DROP TRIGGER IF EXISTS trg_ledger_entries_double_entry ON ledger_entries;
DROP FUNCTION IF EXISTS wallet_enforce_double_entry_transaction();
