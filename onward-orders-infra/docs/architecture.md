# Architecture: Onward Orders on AWS

GitHub renders this Mermaid diagram. To get a PNG for the deliverable, paste it into [mermaid.live](https://mermaid.live) or draw.io and export it as `docs/architecture.png`.

```mermaid
flowchart LR
  dev([Developer]) -->|1 merge to main| gh[GitHub: onward-orders-app]
  gh -->|2 GitHub Actions<br/>OIDC to STS, 1h creds| ecr[(Amazon ECR<br/>onward-orders-lab<br/>:sha immutable, :latest)]
  ecr -->|3 ECR Image Action PUSH latest| eb[EventBridge rule]
  eb -->|4 StartPipelineExecution| cp[CodePipeline V2]
  gh -. appspec.yaml + taskdef.json .-> cp
  cp -->|5 CodeDeployToECS| cd[CodeDeploy<br/>blue/green, canary 10% 5 min<br/>alarms trigger auto rollback]

  subgraph VPC["VPC 10.20.0.0/16 (eu-west-1)"]
    direction TB
    subgraph AZa["AZ eu-west-1a"]
      pubA[Public subnet 10.20.0.0/24]
      privA[Private subnet 10.20.10.0/24<br/>Fargate task + endpoint ENIs]
    end
    subgraph AZb["AZ eu-west-1b"]
      pubB[Public subnet 10.20.1.0/24]
      privB[Private subnet 10.20.11.0/24<br/>Fargate task + endpoint ENIs]
    end
    alb{{Internet-facing ALB<br/>:80 prod, :8080 test}}
    blue[Target group BLUE]
    green[Target group GREEN]
    vpce[Interface endpoints:<br/>ecr.api, ecr.dkr, logs]
    s3gw[S3 gateway endpoint]
  end

  users([Customers]) -->|HTTP| alb
  alb --- pubA & pubB
  alb --> blue & green
  blue --> privA & privB
  green --> privA & privB
  cd -->|6 new task set in green,<br/>shift listener traffic| alb
  privA & privB -->|443, endpoint-sg| vpce
  privA & privB -->|443, S3 prefix list| s3gw
  vpce -.-> ecr
```

## Numbered flow of a change

1. A developer merges to `main` in **onward-orders-app**. This is the only manual step.
2. **GitHub Actions** runs the tests, then assumes `onward-orders-lab-github-actions-role` through **OIDC**. It gets temporary STS credentials, with no stored keys. It builds the image and pushes `:<sha>` (immutable) and `:latest` to **ECR**.
3. ECR emits an **ECR Image Action PUSH** event for `latest`.
4. The **EventBridge** rule starts **CodePipeline**. There is no polling.
5. The pipeline collects the image URI from ECR, plus `appspec.yaml` and `taskdef.json` from the app repo. It then registers a new task definition revision and calls **CodeDeploy**.
6. **CodeDeploy** starts a green task set in the private subnets of both AZs and registers it in the idle target group. It shifts 10% of production traffic for 5 minutes, then 100%. If a 5XX or unhealthy-host alarm fires, it rolls back automatically. The old tasks stay up 5 minutes for a fast rollback, then terminate.

## Security boundaries

- The **ALB** is the only public resource. Tasks get no public IP, and private route tables have no `0.0.0.0/0` route. There is no NAT gateway.
- Security groups are chained: `alb-sg` reaches `task-sg` on 8080 only. `task-sg` reaches `endpoint-sg` and the S3 prefix list on 443 only. `endpoint-sg` accepts 443 only from `task-sg`.
- IAM uses managed policies only. The GitHub role is trusted only for `repo:Ndaziramiyep/onward-orders-app:ref:refs/heads/main`.
