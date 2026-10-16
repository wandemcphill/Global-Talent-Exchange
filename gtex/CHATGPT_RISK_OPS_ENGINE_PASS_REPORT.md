# ChatGPT Risk Ops Engine Pass Report

This pass adds a broader compliance and operational safety layer:

- AML case registry
- Fraud case registry
- System event registry
- Audit log registry
- User and admin risk overview endpoints
- Automated scan across treasury, gifting, and reward density surfaces
- Admin resolution workflow for AML and fraud cases

Main route families:
- `/risk-ops/me/*`
- `/admin/risk-ops/*`

Migration:
- `backend/migrations/versions/20260314_0033_risk_ops_engine.py`
