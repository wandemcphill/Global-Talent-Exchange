from backend.scripts.audit_identity_compliance_boundary import main


def test_identity_compliance_boundary_audit_passes():
    assert main() == 0
