# GTEX AML / Identity Policy

GTEX applies risk-based controls to deposits, withdrawals, trading, unusual account activity, linked devices, and abnormal value flows.

## Identity verification authority

KYC verification is **not** established by a client-authored status value or by an administrator directly flipping a boolean/status field.

The authoritative verification path is `IdentityComplianceService`. A verified decision requires:

- DIDit as the approved identity provider
- a non-empty provider subject/reference
- an explicit provider decision of `verified`
- a timezone-aware verification timestamp that is not in the future
- non-expired evidence when an expiry is supplied
- structured check results
- an append-only `AuditLog` decision record

The `User.kyc_status` field is a compatibility projection of the decision. Direct mutation through `UserService.set_kyc_status()` is disabled and fails closed.

## Risk-based controls

Controls may include:
- KYC review
- transaction holds
- source-of-funds questions
- manual admin review
- suspicious activity escalation
- wallet freezes
- withdrawal blocks
- trading blocks

A missing, invalid, expired, or unverifiable identity decision must be treated as **not verified**. The platform must not infer verification from profile existence, uploaded-file presence, account age, or an untrusted client payload.
