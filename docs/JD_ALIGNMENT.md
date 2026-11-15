# LSK AI Access Operations — Senior AI Platform Engineer JD alignment

## What is implemented
- Tenant-scoped access requests and reviewer approvals with signed OIDC JWT scopes and separation of duties.
- PostgreSQL request and audit record persistence.
- Optional Gemini read-only advisory; only a reduced resource label and permission are shared.
- Cloud Run/Cloud SQL/Secret Manager/Artifact Registry/Terraform infrastructure, CI tests and WIF image publishing.

## How this matches the Brixton position
- **Security/IAM:** implemented a request and approval control plane, not actual external directory provisioning.
- **AI and automation:** live Vertex AI SDK integration path exists; advice is non-authoritative, never executes access changes.
- **Database:** auditable transaction-backed request store; tenancy enforced in API queries.
- **IT/systems:** controlled infrastructure pipeline and dedicated runtime identity.
- **Networking:** hosting connection scaffold only, not network engineering depth or private-cloud architecture.
- **Autonomous teams:** users request access without support tickets; fulfillment is not automatic.

## Critical engineering gaps
1. Integrate a sandbox identity provider (OIDC + SCIM) and implement grant/revoke with audited, timed approval and expiry.
2. Create bounded MCP-compatible tools for read-only IAM troubleshooting (list policy, groups, decisions and recent failures), capture evidence and model evaluations. Add prompt injection tests, human approval for write actions.
3. Implement policy-as-code, role lifecycle, recertification and SoD negative test suites.
4. Provide private networking with a defined VPC threat boundary, Cloud Logging/Monitoring alerts, recovery exercises and SLO metrics.
5. Deploy in GCP with synthetic identities; collect real tests, latency, cost, and security evidence.

## Current limitations
Approval updates only the application's database; no external IAM permission is granted or revoked. AI advice is optional and can fail separately without changing the decision. Never claim autonomous remediation or enterprise certification from this lab.
