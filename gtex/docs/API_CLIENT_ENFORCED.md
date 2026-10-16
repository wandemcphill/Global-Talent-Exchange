# API Client Enforcement

- Canonical endpoint contract lives in `/shared/api_contract.json`.
- Flutter web and mobile share the generated binding at `/frontend/lib/data/generated/gte_api_contract.g.dart`.
- Runtime endpoint resolution now goes through `/frontend/lib/data/gte_api_contract.dart`.
- Shared transport helpers attach `X-API-Version: 2` automatically for canonical `/api/v2/*` requests.
- The shared Flutter repositories now resolve endpoints through the contract instead of ad hoc `/api/v1` rewriting.
- CI now regenerates the contract binding and fails if real frontend client code references deprecated or undeclared internal routes.
- Fixture-only route shims are explicitly excluded from the contract checker so the gate stays strict on live clients without misclassifying local fake transports.
