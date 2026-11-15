# LSK AI Access Operations Platform

**Active branch:** `feature/aws`, native AWS dev/staging/prod configuration. See the [Release Matrix](docs/RELEASE_MATRIX.md), [AWS Deployment Guide](docs/DEPLOY_AWS.md). internal HTTPS ALB restricted by security groups restricts network reachability; application OIDC/JWT and tenant checks authorize people. Amazon Bedrock returns optional read-only advice and cannot approve access. Cloud resources and compliance were not live-verified.


Independent portfolio lab: fictional LSK IAM. Not evidence of an actual employer deployment.

AWS target: FastAPI, PostgreSQL, ECS Fargate, Amazon RDS PostgreSQL, AWS Secrets Manager, Amazon ECR, Terraform, GitHub Actions WIF.

## Security
OIDC-signed JWT, tenant and scope isolation, no payment processing, synthetic data. Restrict ECS Fargate invoker IAM. Do not commit secrets.

## Cost
Create a billing budget first. Amazon RDS PostgreSQL is charged while running. Budget alerts do not cap spending. No infrastructure is automatically deployed by this repository.

## Development
Run pip install -r requirements-dev.txt and DATABASE_URL=sqlite+pysqlite:///./test.db python -m pytest -q . See docs/ for design, operating risks, and interview guidance.


---

## Shared AWS request path

The diagrams below describe the **deployed configuration**, not a claim that this repository is currently running in AWS. The local Docker Compose environment substitutes a local PostgreSQL container for Amazon RDS PostgreSQL.

```mermaid
flowchart LR
  U["Caller with valid credentials"] --> I["ECS Fargate invoker IAM"]
  I --> R["ECS Fargate: FastAPI"]
  R --> J["Verify signed OIDC JWT, tenant_id, scope"]
  J --> H["Endpoint business rules"]
  H <--> D[("Amazon RDS PostgreSQL")]
  R -. "Runtime DATABASE_URL secret" .-> S["AWS Secrets Manager"]
  H --> O["JSON HTTP response"]
```

**Trust boundaries and components:** internal HTTPS ALB restricted by security groups determines whether a principal may invoke the deployed service. FastAPI **separately** checks a signed RS256 OIDC access JWT (issuer, audience, expiry, subject, tenant, and required scopes). An invoker identity token alone is not a substitute for the application's access token. Pydantic validates request bodies; the SQLAlchemy session reads/writes PostgreSQL with tenant filters. The application returns a synchronous JSON response. Terraform configures the ECS Fargate runtime service account, Amazon RDS PostgreSQL connection, AWS Secrets Manager and Amazon ECR; GitHub Actions builds/publishes containers through Workload Identity Federation. These CI/deployment components are **not** invoked by normal customer API calls.

**Operational endpoints:** `GET /healthz` responds without querying the database; `GET /readyz` queries the database. A local schema bootstrap is provided by `scripts/migrate.py`, not by incoming requests. Schema bootstrap is not a reviewed Alembic migration strategy.

**No frontend UI is included.** Use an authorized REST client or the FastAPI OpenAPI interface for the lab. No live employer integrations, real customer data, or real funds are involved.

## Business workflow: request access, obtain review, and inspect the audit trail

**Use case:** An employee requests corporate application access. An independent reviewer approves the **request record**, not an external IAM grant. Optional Amazon Bedrock advice is informational.

```mermaid
sequenceDiagram
  autonumber
  participant U as Employee
  participant I as internal HTTPS ALB restricted by security groups
  participant A as FastAPI / OIDC
  participant DB as Amazon RDS PostgreSQL
  participant M as Amazon Bedrock Amazon Bedrock (optional)
  participant R as Independent reviewer
  U->>I: POST /v1/access-requests
  I->>A: Permit invoker
  A->>A: Verify access:request + tenant + allowed permission
  A->>DB: INSERT access_requests pending + audit requested
  DB-->>A: Commit request ID
  A-->>U: 201 {id,status:pending}
  opt Authorized read-only AI advisory
    U->>A: GET /v1/access-requests/{id}/ai-advisory
    A->>A: Require access:analyze + same tenant
    A->>M: Reduced resource label + requested permission
    M-->>A: Security suggestion, not approval
    A-->>U: advisory + automated_decision=false
  end
  R->>I: POST /v1/access-requests/{id}/approve
  I->>A: Permit invoker
  A->>A: Require access:approve and different requester
  A->>DB: Lock pending request; set approved + audit approved
  DB-->>A: Commit reviewer identity
  A-->>R: 200 {status:approved,provisioned:false}
  R->>A: GET /v1/audit
  A->>DB: SELECT tenant-scoped events
  DB-->>A: Requested and approved events
  A-->>R: Audit JSON
```

### Component-by-component behavior

| Stage | Code/component | Action and guardrail | Result |
|---|---|---|---|
| 1 | internal HTTPS ALB restricted by security groups + FastAPI `get_principal()` | Invoker IAM followed by signed JWT verification | Allowed tenant and subject |
| 2 | `AccessRequestNew` / `request_access()` | Validate resource, justification and permission in `viewer`, `editor`, `operator` | New `pending` request |
| 3 | `AccessRequest` + `AuditEvent` tables | Store request and `requested` audit event in one DB transaction | Durable request ID |
| 4 | Optional `advisory()` -> `app/ai.py` | Requires `access:analyze`; query request in same tenant | Model-generated security advice only |
| 5 | Amazon Bedrock Amazon Bedrock (optional) | Receives requested permission and truncated resource label; no identity or justification in prompt | Advisory text; may fail when model unavailable |
| 6 | `approve()` | Requires `access:approve`; row lock; requester cannot approve their own request; must be pending | `approved` status and reviewer identity |
| 7 | `audit()` | Requires `access:audit`; tenant-filtered event list | Request/approval audit entries |

### API example

```http
POST /v1/access-requests
Authorization: Bearer <OIDC_ACCESS_JWT>
Content-Type: application/json

{"resource":"finance-reporting","permission":"viewer","justification":"Read monthly close reports"}
```

The API responds with a request `id` and `status:"pending"`. A **different authorized user** invokes:

```http
POST /v1/access-requests/REQUEST_ID/approve
Authorization: Bearer <REVIEWER_OIDC_ACCESS_JWT>
```

It returns `{"id":"...","status":"approved","provisioned":false}`. The reviewer can use `GET /v1/audit` to inspect tenant events. For advisory, call `GET /v1/access-requests/REQUEST_ID/ai-advisory` using `access:analyze`.

### Failure behavior and boundaries

- Missing JWT/invalid signature: 401; insufficient scope or missing tenant: 403.
- Invalid permission: 422. Cross-tenant or unknown request: 404.
- Self approval: 403; duplicate approval or non-pending state: 409.
- No Amazon Bedrock configuration: 503; model failure: 502. Access review works without an AI response.
- **Not implemented:** identity provider group grants, IAM provisioning or revocation, periodic access recertification, approval expiry, full request lifecycle, or AI autonomous remediation. This approval changes only **local database state**.
- The model returns **untrusted explanatory text**, not a policy decision. It does not execute tools or issue permissions.


## Brixton JD alignment

See [capability review and acceptance criteria](docs/JD_ALIGNMENT.md). LSK is a fictional portfolio company; employer deployments are not represented.


## Multinational deployment safeguards

The LSK reference deployment supports an explicit region/tenant authorization gate and configurable Amazon RDS PostgreSQL HA sizing. Read the [multinational operating standard](docs/MULTINATIONAL_DEPLOYMENT.md) before creating regional stacks. No automatic cross-region replication or failover is configured; regional legal approval, private connectivity and operational testing remain mandatory.

## Database migration process (updated)

This repository now uses **versioned Alembic migrations**, not `Base.metadata.create_all()` for cloud initialization. A dedicated PostgreSQL 16 CI job verifies the baseline schema and database-specific constraints. Run `python scripts/migrate.py` in a separately approved one-off job, **before** routing application traffic, and record the revision through `python -m alembic current`. For an existing database created by the earlier bootstrap, use the [brownfield migration checklist](docs/SCHEMA_MIGRATION.md) before changing it. Production deployment also requires backup/restore, private network, controlled change release and legal/region reviews.

## Private regional database connectivity

An opt-in [private Amazon RDS PostgreSQL + Direct VPC egress deployment](docs/PRIVATE_DATABASE_NETWORK.md) is available. Set `enable_private_sql=true` with a reviewed non-overlapping subnet CIDR. A `prod` Terraform plan now **requires** private SQL, REGIONAL HA and a non-micro Amazon RDS PostgreSQL tier. This is still a lab reference until a real AWS plan/apply, approved security review, failover test and backup restore have been completed.


## Optional private Amazon EKS Kubernetes infrastructure

This AWS branch includes a [reusable EKS Terraform cluster module](docs/KUBERNETES_INFRASTRUCTURE.md) under `modules/eks/`, instantiated from `infra/kubernetes/` using `environments/kubernetes/{dev,staging,prod}.tfvars`. It provides isolated VPC/subnets, private Kubernetes API endpoint, NAT egress, managed node groups, explicit IAM API access, and control-plane audit logs. A dedicated **EKS Kubernetes environment plan and apply** workflow operates with AWS workload identity and a separate S3 state key for each protected environment.

**The existing ECS Fargate application stack remains unchanged.** Provisioning an EKS cluster does not deploy the business API, install IRSA/Pod Identity add-ons, wire private ingress, establish application secrets, or implement GitOps. Those release responsibilities require a separate Helm/Argo CD pipeline and live network/security testing. CI validated the Terraform module; no EKS infrastructure has been applied to an AWS account.
