# access — interview defense

Portfolio project only, not a historical company production deployment.

1. Show local unit tests and a negative authorization test.
2. Explain how Cloud Run invoker IAM and signed OIDC scopes protect different trust boundaries.
3. Explain why SQL uniqueness/transactions matter for idempotency and approvals.
4. Explain Cloud Run vs GKE tradeoffs, Cloud SQL cost and HA limitations.
5. Demonstrate the optional Vertex/Gemini read-only advisory endpoint. Explain its permission scope, what limited context reaches the model, failure handling, and why it cannot approve or provision IAM. Actual infrastructure-operations tools, prompt-injection evaluation, and policy enforcement remain future work.
6. Production gaps: migrations, HA, disaster recovery, private networking, SLO/alert policies, stress tests, tenant isolation and security assessment.
