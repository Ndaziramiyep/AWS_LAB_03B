# Onward Logistics: Safe Order System Delivery on AWS
### Implementation Guide and Roadmap (ECS Fargate, CloudFormation GitSync, GitHub Actions OIDC, CodePipeline, CodeDeploy Blue/Green)

---

## Table of Contents
1. [Lab at a Glance](#1-lab-at-a-glance)
2. [Requirements Traceability Matrix](#2-requirements-traceability-matrix)
3. [Target Architecture](#3-target-architecture)
4. [Repository Layout](#4-repository-layout)
5. [Roadmap (Phases 0-9)](#5-roadmap)
6. [Code Reference Snippets](#6-code-reference-snippets)
7. [Cost Analysis and Rejected Alternatives](#7-cost-analysis-and-rejected-alternatives)
8. [Verification and Live Demo Script](#8-verification-and-live-demo-script)
9. [Common Pitfalls](#9-common-pitfalls)
10. [Deliverables and Rubric Checklist](#10-deliverables-and-rubric-checklist)

> **Note:** The *Client Profile: Onward Logistics* (naming and tag standards) was not included in the material provided. Wherever you see `<NAMING>` or `<TAGS>`, apply the standards from that document. Prices in Section 7 are approximate. Confirm them with the AWS Pricing Calculator for your region.

---

## 1. Lab at a Glance

| Item | Detail |
|---|---|
| Goal | Every approved change reaches customers automatically, safely, with zero downtime and easy rollback |
| App | Single full-stack container (UI + order logic), Python or Java per your assigned stack, showing **your full name + lab name** |
| Compute | Amazon ECS on Fargate, tasks in **private subnets**, behind an **internet-facing ALB** |
| Network | **No NAT gateway.** VPC endpoints for AWS service access. No route to the internet from private subnets |
| IaC | **CloudFormation only**, deployed through **CloudFormation GitSync**. No console-created resources |
| CI | GitHub Actions builds the image and pushes to ECR, authenticating with **OIDC** (no long-lived keys) |
| CD | **EventBridge** triggers **CodePipeline**, which runs **CodeDeploy blue/green** on ECS |
| Repos | **Two separate repos:** infrastructure and application |
| IAM rule | **No inline policies** anywhere. Use customer-managed or AWS-managed policies only |
| Scoring | Discovery 20% / Solution 50% / Diagram 10% / Live review 20% |

### Stakeholder needs distilled

| Stakeholder | Key demand | How you meet it |
|---|---|---|
| **CTO** | Merge is the only manual step. No outage on release. Fast rollback. Readable for new engineers | GitHub Actions, then ECR, EventBridge, CodePipeline, CodeDeploy blue/green with auto-rollback. Clean repo structure and READMEs |
| **Head of Security** | No long-lived credentials. One public entry point. App has no internet path | GitHub OIDC, ALB as the only public resource, private subnets without a default route, VPC endpoints |
| **Head of Operations** | Survives container or AZ failure. Scales without manual action | Min 2 tasks across 2+ AZs, ALB health checks, ECS service auto scaling (target tracking) |
| **Finance Lead** | Idle environments cost nothing. Understand endpoint cost | Teardown or scale-to-zero strategy, cost breakdown (Section 7) |

---

## 2. Requirements Traceability Matrix

Use this to make sure nothing is missed, and as a map for the live review.

| # | Requirement | Where it is satisfied | Evidence for demo |
|---|---|---|---|
| R1 | All infra in CloudFormation | `infra-repo/templates/*.yaml` | Stack list in console, no manual resources |
| R2 | Deployed via GitSync | One GitSync config per stack (`deployment-*.yaml`) | Push to infra repo, stack updates itself |
| R3 | HA + strict security | Multi-AZ subnets, 2+ tasks, SG chaining, no NAT/IGW route for private | Route tables, SG rules |
| R4 | App shows full name + lab name | `app-repo/app/` | Browser screenshot on ALB DNS |
| R5 | ECS Fargate in private subnets behind internet-facing ALB | `ecs.yaml`, `alb.yaml` | Task ENIs have no public IP |
| R6 | VPC endpoints, no NAT | `network.yaml` | No NAT in VPC, endpoints listed |
| R7 | GitHub Actions to ECR via OIDC | `.github/workflows/build-push.yaml` + OIDC role | Workflow run, no secrets in repo settings |
| R8 | EventBridge, CodePipeline, CodeDeploy blue/green | `delivery.yaml` | Pipeline execution, deployment console |
| R9 | Separate repos | Two repos | Show both |
| R10 | Company standards (naming and tags) | `Tags`, naming parameters | Tag editor / resource tags |
| R11 | No inline policies | Only `AWS::IAM::ManagedPolicy` and `ManagedPolicyArns` | `grep -R "Policies:" templates/` returns nothing |
| R12 | Autoscaling out and in | `autoscaling.yaml` | Load test, task count changes |
| R13 | Rollback | CodeDeploy auto-rollback and manual stop/rollback | Deploy a broken image |
| R14 | Rebuildable from repos | Ordered stack creation documented in README | Recreate from scratch (or explain order) |

---

## 3. Target Architecture

```
                         Developer
                            │ git push (main)
                            ▼
                  ┌───────────────────┐
                  │  GitHub: app repo │
                  └─────────┬─────────┘
                            │ GitHub Actions
                            │ (OIDC → STS → temp creds)
                            ▼
                  ┌───────────────────┐   ECR "Image Action: PUSH"
                  │    Amazon ECR     │──────────────┐
                  └───────────────────┘              ▼
                                            ┌─────────────────┐
                                            │   EventBridge   │
                                            └────────┬────────┘
                                                     ▼
                              ┌───────────────────────────────────────┐
                              │              CodePipeline             │
                              │ Source(ECR) + Source(app repo files)  │
                              │          → Deploy (CodeDeployToECS)   │
                              └──────────────────┬────────────────────┘
                                                 ▼
                                        ┌─────────────────┐
                                        │   CodeDeploy    │ blue/green, canary/linear,
                                        │  (ECS platform) │ alarms → auto rollback
                                        └────────┬────────┘
                                                 │ shifts ALB listener traffic
══════════════════════════════ VPC ═════════════════════════════════════════════
 Internet ──► ALB (public subnets, AZ-a / AZ-b[/c])
               │ :80/443 prod listener      :8080 test listener
               ├──► Target Group BLUE ──┐
               └──► Target Group GREEN ─┤
                                        ▼
        Private subnets (no 0.0.0.0/0 route)
        ┌─────────────────────────────────────────────┐
        │  ECS Fargate tasks (AZ-a)   (AZ-b)  ...     │
        └───────┬─────────────────────────────────────┘
                │ private connectivity only
                ▼
     VPC Endpoints:  ecr.api (iface) | ecr.dkr (iface)
                     logs (iface)    | s3 (gateway)
                     [optional: ssm / secretsmanager / monitoring]
```

### Design decisions at a glance

- **Subnets:** 2 public (ALB only) + 2 private (tasks and endpoints) across at least 2 AZs.
- **Private route tables:** only a local route, plus the S3 gateway endpoint prefix-list route. **No `0.0.0.0/0`.**
- **Security groups (chained, least privilege):**
  - `alb-sg`: inbound 80/443 from `0.0.0.0/0`. Outbound to `task-sg` on 8080.
  - `task-sg`: inbound 8080 **only from `alb-sg`**. Outbound 443 to `endpoint-sg` and the S3 prefix list.
  - `endpoint-sg`: inbound 443 **only from `task-sg`**.
- **ECS service:** `DeploymentController: CODE_DEPLOY`, desired count 2 or more, spread across AZs.
- **ALB:** two target groups (blue and green, target type `ip`), a production listener, and a test listener (for example 8080) used by CodeDeploy for pre-shift validation.

---

## 4. Repository Layout

### Repo 1: `onward-orders-infra` (CloudFormation + GitSync)

```
onward-orders-infra/
├── README.md                      # How pieces fit, stack order, how to rebuild
├── docs/
│   ├── architecture.png           # Diagram deliverable
│   └── cost-analysis.md
├── templates/
│   ├── 01-foundation.yaml         # OIDC provider, GitHub role, ECR repo, managed policies
│   ├── 02-network.yaml            # VPC, subnets, route tables, SGs, VPC endpoints
│   ├── 03-alb.yaml                # ALB, listeners, blue/green target groups
│   ├── 04-ecs.yaml                # Cluster, task def (bootstrap), service, log group, roles
│   ├── 05-autoscaling.yaml        # Scalable target + target-tracking policies
│   └── 06-delivery.yaml           # CodeDeploy, CodePipeline, EventBridge rule, artifact bucket
└── deployments/                   # GitSync deployment files (one per stack)
    ├── 01-foundation.deployment.yaml
    ├── 02-network.deployment.yaml
    └── ...
```

### Repo 2: `onward-orders-app` (application + CI)

```
onward-orders-app/
├── README.md
├── .github/workflows/build-push.yaml
├── app/                           # Flask (Python) or Spring Boot (Java)
│   ├── main.py / pom.xml ...
│   ├── templates/index.html       # Shows full name + lab name
│   └── requirements.txt
├── Dockerfile
├── appspec.yaml                   # Consumed by CodeDeploy
└── taskdef.yaml                   # Task definition template with IMAGE1_NAME placeholder
```

> **Why the pipeline needs `appspec.yaml` and `taskdef.yaml`:** the `CodeDeployToECS` action requires an AppSpec file and a task definition template. The ECR source provides only the image reference, so you pair it with a second source (your app repo or an S3 object) for the two template files. Both templates are written in YAML in this guide, and the action is pointed at them with `AppSpecTemplatePath: appspec.yaml` and `TaskDefinitionTemplatePath: taskdef.yaml`. If your pipeline rejects a YAML task definition, check the current CodePipeline documentation for supported formats.

---

## 5. Roadmap

Suggested pacing: one phase per sitting. Phases 2 to 6 are the bulk of the work.

### Phase 0: Discovery Report (before building) — worth 20%

Complete the **Discovery Report Template** *before* touching AWS.

**Part A: What you found**
- Common solutions for safe delivery: manual deploys, scripts, rolling updates, blue/green, canary, Jenkins/GitLab CI, ECS native blue/green, Elastic Beanstalk, App Runner.
- What happens with *no* solution: slow, error-prone releases, downtime, credential leakage, no rollback, release fear on peak days, inconsistent environments.
- Cite sources (AWS docs, Well-Architected, case studies).

**Part B: Business value**
- Chosen approach: ECS Fargate + CodeDeploy blue/green + GitSync + OIDC + VPC endpoints.
- Services and *why*: ALB (single entry point), Fargate (no servers), ECR (private registry), VPC endpoints (no internet path), CodePipeline/CodeDeploy (managed zero-downtime releases), EventBridge (event-driven trigger), CloudFormation GitSync (auditable IaC).
- Who benefits: CTO, Security, Operations, Finance, customers, engineers.
- Link each AWS service to a stakeholder quote.

**Done when:** report link ready, with sources.

---

### Phase 1: Repos, Foundation, and OIDC (no long-lived keys)

1. Create both GitHub repositories (infra and app).
2. **Connect GitSync:** create an AWS CodeConnections (GitHub) connection. *The one-time GitHub authorization handshake is a console action. It is a connection to GitHub, not an infrastructure resource, so document it in the README.*
3. Create the **GitSync IAM role** (customer-managed policy attached, not inline) that CloudFormation assumes to sync from the repo and create stacks.
4. Author `01-foundation.yaml`:
   - `AWS::IAM::OIDCProvider` for `token.actions.githubusercontent.com` (audience `sts.amazonaws.com`).
   - GitHub Actions IAM role with a trust policy scoped to `repo:<org>/<app-repo>:ref:refs/heads/main`.
   - `AWS::IAM::ManagedPolicy` granting **only** ECR push to the specific repository, plus `ecr:GetAuthorizationToken` on `*`.
   - `AWS::ECR::Repository` with scan-on-push, a lifecycle policy, and immutable tags (see Phase 7).
5. Add the GitSync deployment file and push. The stack deploys itself.

**Done when:** foundation stack is `CREATE_COMPLETE` via GitSync and no access keys exist anywhere.

---

### Phase 2: Network (private, HA, no NAT)

`02-network.yaml`:
- VPC with DNS support and DNS hostnames **enabled** (required for interface endpoint private DNS).
- Public subnets in 2+ AZs (ALB), with an Internet Gateway and public route table.
- Private subnets in the same AZs. Route tables with **no default route**.
- **Endpoints:**

| Endpoint | Type | Why Fargate needs it |
|---|---|---|
| `com.amazonaws.<region>.ecr.api` | Interface | ECR API calls and auth |
| `com.amazonaws.<region>.ecr.dkr` | Interface | Docker registry (image manifests) |
| `com.amazonaws.<region>.s3` | **Gateway** | ECR image layers are stored in S3 (free) |
| `com.amazonaws.<region>.logs` | Interface | `awslogs` log driver to CloudWatch |
| *(optional)* `ssm`, `secretsmanager`, `monitoring` | Interface | Only if the app uses them |

- Interface endpoints: `PrivateDnsEnabled: true`, placed in **every private subnet/AZ**, attached to `endpoint-sg`.
- Optionally restrict the S3 endpoint policy to the ECR layer buckets. A customer-managed policy document on the endpoint is acceptable (it is a resource policy, not an IAM inline policy).
- Export subnet IDs, VPC ID, and SG IDs (`Outputs` + `Export`), or write them to SSM Parameter Store.

**Done when:** private route tables show no `0.0.0.0/0` and no NAT gateway exists.

---

### Phase 3: Application and Container Image

- Build a single full-stack app (Python Flask or Java Spring Boot) listening on **8080**.
- `GET /` renders the page: **"Your Full Name, Lab: Delivering Order System Updates Safely"**. Also show an app version, such as the git SHA from a build arg, which makes blue/green visible in the demo.
- `GET /health` returns `200` and is used by the ALB health check.
- Optional demo helpers: `/slow` or `/cpu` (to burn CPU for the autoscaling demo), and a build-arg switch that makes `/health` fail (to demo a bad release and rollback).
- Dockerfile: multi-stage, slim base image, non-root user, `EXPOSE 8080`, `HEALTHCHECK` optional.
- Test locally with `docker build` and `docker run -p 8080:8080`.

**Done when:** container runs locally and shows your name and the lab name.

---

### Phase 4: Push the First Image (Bootstrap)

Because tasks sit in private subnets with no internet path, **the image must already exist in ECR before the ECS service can start**. Order of operations:

1. Foundation stack is up (ECR + OIDC role).
2. Add the GitHub Actions workflow (Section 6.3) to the app repo and push, which builds and pushes the first image.
3. Only then create the ECS stack.

> If the pipeline's first run starts before the service exists, that is expected. Either deploy the service first, or let the first pipeline run fail and re-trigger it. Document the chosen approach in the README.

---

### Phase 5: ALB and ECS Fargate Service

`03-alb.yaml`
- Internet-facing ALB in public subnets, `alb-sg`.
- Two target groups: `blue` and `green`, `TargetType: ip`, port 8080, health check path `/health`.
- Listener **prod** (80, or 443 with ACM cert if a domain is available) forwarding to blue.
- Listener **test** (8080) forwarding to green (used for pre-traffic validation).

`04-ecs.yaml`
- `AWS::ECS::Cluster` (Container Insights enabled).
- `AWS::Logs::LogGroup` with a retention period.
- **IAM roles (no inline policies):**
  - *Task execution role*: `ManagedPolicyArns` containing `arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy`.
  - *Task role*: least privilege via a separate `AWS::IAM::ManagedPolicy` (may be near-empty if the app calls no AWS APIs).
- `AWS::ECS::TaskDefinition` (Fargate, `awsvpc`, CPU/memory sized deliberately, for example 256/512 for a demo, and justify it).
- `AWS::ECS::Service`:
  - `LaunchType: FARGATE`, `DesiredCount: 2` (minimum), `DeploymentController` type `CODE_DEPLOY`.
  - `NetworkConfiguration`: private subnets, `task-sg`, `AssignPublicIp: DISABLED`.
  - `LoadBalancers`: the **blue** target group.
  - `HealthCheckGracePeriodSeconds` to allow app start.

**Done when:** opening the ALB DNS name in a browser shows your name and the lab name, and the task has no public IP.

---

### Phase 6: Auto Scaling

`05-autoscaling.yaml`
- `AWS::ApplicationAutoScaling::ScalableTarget` (`ecs:service:DesiredCount`, `MinCapacity: 2`, `MaxCapacity: 6`).
- Target-tracking policies:
  - `ECSServiceAverageCPUUtilization` target ~50 to 60%.
  - Optionally `ALBRequestCountPerTarget` for request-driven scaling.
- Tune `ScaleOutCooldown` shorter than `ScaleInCooldown` (for example 60s out, 300s in).
- Application Auto Scaling uses a service-linked role, so reference it by its standard ARN. You do not need to create a role.

> **Operations note:** `MinCapacity: 2` across two AZs is what keeps the service alive through a task failure or AZ loss. Verify both subnets and AZs are used.

---

### Phase 7: Delivery Pipeline (EventBridge → CodePipeline → CodeDeploy)

`06-delivery.yaml`

**CodeDeploy**
- `AWS::CodeDeploy::Application` with `ComputePlatform: ECS`.
- `AWS::CodeDeploy::DeploymentGroup`:
  - Service role with managed policy `AWSCodeDeployRoleForECS`.
  - `DeploymentStyle` with `DeploymentType: BLUE_GREEN` and `DeploymentOption: WITH_TRAFFIC_CONTROL`.
  - `BlueGreenDeploymentConfiguration`: `TerminateBlueInstancesOnDeploymentSuccess` with a wait time (for example 5 min, which is your rollback window), and `DeploymentReadyOption` set to continue.
  - `LoadBalancerInfo.TargetGroupPairInfoList`: both TGs, prod listener, test listener.
  - `AutoRollbackConfiguration`: enabled on `DEPLOYMENT_FAILURE` and `DEPLOYMENT_STOP_ON_ALARM`.
  - `AlarmConfiguration`: CloudWatch alarms such as ALB target 5XX count and unhealthy host count.
- Deployment config: `CodeDeployDefault.ECSCanary10Percent5Minutes` or `ECSLinear10PercentEvery1Minutes` (safer than all-at-once, so explain your choice).

**CodePipeline**
- Artifact S3 bucket (encrypted, block public access, versioned) + pipeline service role (managed policy).
- Stages:
  1. **Source**
     - Action A: provider `ECR` (repo + image tag), output `ImageArtifact` (contains the image details).
     - Action B: provider `CodeStarSourceConnection` (app repo, branch `main`), **`DetectChanges: false`**, output `SourceArtifact` (contains `appspec.yaml` and `taskdef.yaml`).
  2. **Deploy**: provider `CodeDeployToECS`, with `ApplicationName`, `DeploymentGroupName`, `TaskDefinitionTemplateArtifact`, `AppSpecTemplateArtifact`, `AppSpecTemplatePath: appspec.yaml`, `TaskDefinitionTemplatePath: taskdef.yaml`, `Image1ArtifactName: ImageArtifact`, `Image1ContainerName: IMAGE1_NAME`.

**EventBridge**
- Rule on ECR push events (pattern in Section 6.4), target = the pipeline, role = a customer-managed policy allowing `codepipeline:StartPipelineExecution` on that pipeline.
- Set the ECR source action's change detection to rely on EventBridge so there is no polling.

**Tagging strategy (rollback and traceability)**
- GitHub Actions pushes `:<git-sha>` (immutable, audit trail) and `:latest` (what the ECR source watches).
- Rolling back = redeploy a previous SHA, or stop and roll back the in-progress CodeDeploy deployment.

**Done when:** a push to `main` in the app repo produces a new running version with no human action.

---

### Phase 8: Hardening and Standards Pass

- [ ] `grep -R "Policies:" templates/` returns **zero** hits (no inline policies). Never use `AWS::IAM::Policy`, because it creates inline policies.
- [ ] No IAM users and no access keys. No AWS secrets in GitHub repo/environment settings.
- [ ] Naming convention and mandatory tags on **every** taggable resource (use stack-level `Tags` or a `Parameters` map).
- [ ] Parameters with sensible defaults, `Description`s, `Metadata` groupings, and `Outputs` for readability.
- [ ] Encrypted S3 artifact bucket, ECR scanning, log retention.
- [ ] Run `cfn-lint` (and optionally `cfn-guard`) in a GitHub Action on the infra repo.
- [ ] READMEs: purpose, diagram, stack order, how to rebuild, how to roll back, how to run the demo.

---

### Phase 9: Architecture Diagram, Dry Run, and Review Prep — worth 10% and 20%

- Diagram must show: **VPC, AZs, public and private subnets, ALB, ECS tasks, VPC endpoints, ECR, the delivery pipeline (GitHub Actions, ECR, EventBridge, CodePipeline, CodeDeploy), and the numbered flow of a change.**
- Rehearse every client check (Section 8) at least once, including breaking a release.
- Prepare to defend: sizing, scaling triggers, deployment config choice, endpoint choices, rejected alternatives, cost.

---

## 6. Code Reference Snippets

> Starting points. Adapt names, parameters, and tags to the company standards.

### 6.1 OIDC provider, role, and managed policy (no inline policies)

```yaml
Parameters:
  GitHubOrg:
    Type: String
  AppRepo:
    Type: String

Resources:
  GitHubOidcProvider:
    Type: AWS::IAM::OIDCProvider
    Properties:
      Url: https://token.actions.githubusercontent.com
      ClientIdList:
        - sts.amazonaws.com

  EcrRepo:
    Type: AWS::ECR::Repository
    Properties:
      RepositoryName: onward-orders
      ImageScanningConfiguration:
        ScanOnPush: true

  EcrPushPolicy:
    Type: AWS::IAM::ManagedPolicy
    Properties:
      PolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Action: ecr:GetAuthorizationToken
            Resource: "*"
          - Effect: Allow
            Action:
              - ecr:BatchCheckLayerAvailability
              - ecr:InitiateLayerUpload
              - ecr:UploadLayerPart
              - ecr:CompleteLayerUpload
              - ecr:PutImage
              - ecr:BatchGetImage
            Resource: !GetAtt EcrRepo.Arn

  GitHubActionsRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal:
              Federated: !Ref GitHubOidcProvider
            Action: sts:AssumeRoleWithWebIdentity
            Condition:
              StringEquals:
                token.actions.githubusercontent.com:aud: sts.amazonaws.com
              StringLike:
                token.actions.githubusercontent.com:sub: !Sub repo:${GitHubOrg}/${AppRepo}:ref:refs/heads/main
      ManagedPolicyArns:            # NOT "Policies:" (that would be inline)
        - !Ref EcrPushPolicy
```

> The `AssumeRolePolicyDocument` is a trust policy, not an inline policy. It is required.

### 6.2 VPC endpoints (excerpt)

```yaml
S3GatewayEndpoint:
  Type: AWS::EC2::VPCEndpoint
  Properties:
    VpcId: !Ref Vpc
    ServiceName: !Sub com.amazonaws.${AWS::Region}.s3
    VpcEndpointType: Gateway
    RouteTableIds:
      - !Ref PrivateRouteTableA
      - !Ref PrivateRouteTableB

EcrDkrEndpoint:
  Type: AWS::EC2::VPCEndpoint
  Properties:
    VpcId: !Ref Vpc
    ServiceName: !Sub com.amazonaws.${AWS::Region}.ecr.dkr
    VpcEndpointType: Interface
    PrivateDnsEnabled: true
    SubnetIds:
      - !Ref PrivateSubnetA
      - !Ref PrivateSubnetB
    SecurityGroupIds:
      - !Ref EndpointSg
# Repeat for ecr.api and logs
```

### 6.3 GitHub Actions workflow (OIDC, no secrets)

```yaml
name: build-and-push
on:
  push:
    branches:
      - main

permissions:
  id-token: write      # required for OIDC
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::<ACCOUNT_ID>:role/<GitHubActionsRole>
          aws-region: <REGION>

      - id: ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push
        env:
          REGISTRY: ${{ steps.ecr.outputs.registry }}
          REPO: onward-orders
        run: |
          docker build --build-arg APP_VERSION=${GITHUB_SHA::7} \
            -t $REGISTRY/$REPO:${GITHUB_SHA::7} \
            -t $REGISTRY/$REPO:latest .
          docker push $REGISTRY/$REPO:${GITHUB_SHA::7}
          docker push $REGISTRY/$REPO:latest
```
> The role ARN and region are not secrets, so they can live in the workflow file. Pin third-party actions to a version or SHA.
> Note: if you make the ECR repo tag-immutable, `:latest` cannot be overwritten. Either keep mutable tags, or use a single immutable `:<sha>` tag and a different trigger design. Decide and document.

### 6.4 EventBridge rule (ECR push → pipeline)

```yaml
EcrPushRule:
  Type: AWS::Events::Rule
  Properties:
    EventPattern:
      source:
        - aws.ecr
      detail-type:
        - ECR Image Action
      detail:
        action-type:
          - PUSH
        result:
          - SUCCESS
        repository-name:
          - onward-orders
        image-tag:
          - latest
    Targets:
      - Arn: !Sub arn:aws:codepipeline:${AWS::Region}:${AWS::AccountId}:${Pipeline}
        Id: StartPipeline
        RoleArn: !GetAtt EventsInvokePipelineRole.Arn
```

### 6.5 `appspec.yaml` and `taskdef.yaml`

```yaml
# appspec.yaml
version: 0.0
Resources:
  - TargetService:
      Type: AWS::ECS::Service
      Properties:
        TaskDefinition: <TASK_DEFINITION>   # replaced by CodeDeploy
        LoadBalancerInfo:
          ContainerName: "app"
          ContainerPort: 8080
```

```yaml
# taskdef.yaml
family: onward-orders
networkMode: awsvpc
requiresCompatibilities:
  - FARGATE
cpu: "256"
memory: "512"
executionRoleArn: arn:aws:iam::<ACCOUNT_ID>:role/<TaskExecutionRole>
taskRoleArn: arn:aws:iam::<ACCOUNT_ID>:role/<TaskRole>
containerDefinitions:
  - name: app
    image: "<IMAGE1_NAME>"       # replaced by CodePipeline with the new image URI
    essential: true
    portMappings:
      - containerPort: 8080
        protocol: tcp
    logConfiguration:
      logDriver: awslogs
      options:
        awslogs-group: /ecs/onward-orders
        awslogs-region: <REGION>
        awslogs-stream-prefix: app
```

### 6.6 Minimal Flask app and Dockerfile

```python
# app/main.py
import os
from flask import Flask, render_template_string
app = Flask(__name__)

PAGE = """<h1>Onward Logistics Order System</h1>
<p>Student: <b>YOUR FULL NAME</b></p>
<p>Lab: Delivering Order System Updates Safely</p>
<p>Version: {{ v }}</p>"""

@app.get("/")
def index(): return render_template_string(PAGE, v=os.getenv("APP_VERSION", "dev"))

@app.get("/health")
def health(): return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```

```dockerfile
FROM python:3.12-slim
ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION PYTHONUNBUFFERED=1
WORKDIR /srv
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn
COPY app/ .
RUN useradd -m appuser
USER appuser
EXPOSE 8080
CMD ["gunicorn", "-b", "0.0.0.0:8080", "-w", "2", "main:app"]
```

### 6.7 GitSync deployment file (excerpt)

```yaml
# deployments/02-network.deployment.yaml
template-file-path: templates/02-network.yaml
parameters:
  VpcCidr: 10.0.0.0/16
tags:
  # Apply the company-standard tags here
  Environment: lab
```

---

## 7. Cost Analysis and Rejected Alternatives

> Approximate **us-east-1** list prices used for reasoning. Always verify in the AWS Pricing Calculator and state your region and assumptions.

### 7.1 Cost components

| Component | Pricing model (approx.) | Idle cost? |
|---|---|---|
| Fargate tasks | Per vCPU-hour + GB-hour, billed per second | Only while tasks run |
| ALB | ~$0.0225/hr + LCU usage | **Yes** (always on) |
| Interface endpoints | ~$0.01/hr **per endpoint per AZ** + ~$0.01/GB processed | **Yes** |
| S3 gateway endpoint | Free | No |
| NAT gateway (*not used*) | ~$0.045/hr per NAT + ~$0.045/GB | Yes |
| ECR | Per GB-month storage | Small |
| CodePipeline / CodeDeploy (ECS) | Pipeline ~$1/month; CodeDeploy for ECS has no extra charge | Small |
| CloudWatch Logs / alarms | Ingestion and storage | Small |

### 7.2 Private connectivity cost (be ready to explain)

Example: 3 interface endpoints (`ecr.api`, `ecr.dkr`, `logs`) × 2 AZs × $0.01/hr × 730 hrs ≈ **$44/month**, plus data processing. A single NAT gateway is ≈ **$33/month + $0.045/GB**, and it does not meet the security requirement (it creates an internet path).

**Position to defend:** endpoints cost a similar or slightly higher fixed amount than one NAT, but they are required by the Head of Security. They give a private AWS-network path, add endpoint-policy control, and have lower per-GB data cost. Cost levers: use only the endpoints you need, and tear down non-prod environments.

### 7.3 "Idle environments should not cost money"

Choose and document one or both:
- **Teardown:** delete the stacks (reverse order) when idle. Everything is rebuildable from the repos. Only this removes ALB and endpoint costs.
- **Scale to zero:** set `MinCapacity`/`DesiredCount` to 0 via parameters or scheduled scaling (saves Fargate cost only, because ALB and endpoints still bill).

### 7.4 Rejected alternatives

| Alternative | Why rejected |
|---|---|
| NAT gateway instead of endpoints | Violates "no path to the internet"; per-GB cost; extra egress risk |
| ECS rolling update (no CodeDeploy) | No traffic shifting, test listener, or alarm-based auto-rollback; explicitly required to use blue/green |
| EC2 launch type | Server patching and capacity management burden; Fargate removes it |
| IAM user keys in GitHub secrets | Long-lived credentials, which Security forbids |
| Public subnets for tasks | Violates "application off the internet" |
| Console deployments / Terraform | Requirement is CloudFormation + GitSync only |
| Nested stacks | GitSync does not upload child templates to S3. Separate stacks with exports are simpler |
| Elastic Beanstalk / App Runner | Less control over networking and the required pipeline components |
| Single AZ | Fails the AZ-loss requirement |

---

## 8. Verification and Live Demo Script

| Client check | How to demonstrate | Expected result |
|---|---|---|
| **One public address; containers private, no internet route** | Open ALB DNS in browser. Show ECS task details (no public IP). Show private route tables | Only the ALB is public; no `0.0.0.0/0` route in private subnets |
| **Push → new version, no manual steps** | Change the version/text in the app repo, push to `main`. Watch Actions, then ECR, then pipeline, then CodeDeploy | New version live; nobody logged in |
| **Zero-downtime release** | Run `while true; do curl -s <ALB>; sleep 1; done` during the deploy | No failed requests; version flips old to new |
| **Reversible bad release** | Push a build whose `/health` fails (or a failing alarm) | CodeDeploy auto-rolls back; or stop and roll back manually; blue keeps serving |
| **No long-lived credentials** | Show GitHub secrets (none for AWS), the OIDC trust policy, no IAM users/keys | Temporary STS creds only |
| **Scale out and in** | Generate load (`hey`, `ab`, or `/cpu` endpoint); watch task count | Tasks increase, then drop after the cooldown |
| **Container failure tolerance** | Stop a task (`aws ecs stop-task`) | ALB keeps serving; ECS replaces the task |
| **AZ-loss tolerance** | Explain and show tasks in 2+ AZs. Optionally stop all tasks in one AZ or remove one AZ from the service temporarily | Service stays up on remaining AZ |
| **Readable by a new engineer** | Walk through the READMEs, layout, and stack order | Clear mapping from objective to template |
| **Cost explanation** | Present Section 7 numbers and rejected alternatives | Clear, defensible reasoning |
| **Rebuildable from repos** | Show the README rebuild order (or perform it) | Same environment from code alone |

---

## 9. Common Pitfalls

1. **Chicken-and-egg image:** The ECS service cannot start with no image in ECR, and private tasks cannot pull from anywhere else. Push the first image *before* creating the service.
2. **Missing endpoints:** Tasks stuck in `PROVISIONING` or `CannotPullContainerError` usually means a missing `ecr.dkr`, `ecr.api`, `logs`, or **S3 gateway** endpoint, or `endpoint-sg` not allowing 443 from `task-sg`.
3. **Private DNS:** The VPC needs DNS support and hostnames on, and the endpoints need `PrivateDnsEnabled: true`.
4. **Inline policy trap:** `Policies:` on a role, and `AWS::IAM::Policy`, both create inline policies. Use `AWS::IAM::ManagedPolicy` + `ManagedPolicyArns`.
5. **CODE_DEPLOY-controlled service:** CloudFormation cannot roll the task definition for you. CodeDeploy owns deployments, so keep the CFN task definition as the bootstrap version and avoid changing it afterwards, or later stack updates may conflict or be blocked. Document this.
6. **OIDC trust too broad:** Always constrain `sub` to your repo and branch.
7. **GitSync is per-stack:** One sync configuration per stack and per deployment file. There is no cross-stack ordering, so create stacks in order and use exports or SSM parameters.
8. **CodeConnections handshake:** The GitHub authorization is a one-time manual step, so document it.
9. **ECR `latest` is mutable:** Pair it with immutable SHA tags for traceability and rollback, or design around SHA-only tags.
10. **Health check grace and startup time:** Set `HealthCheckGracePeriodSeconds`, and make sure the ALB health check path returns 200 quickly, or deployments will flap and roll back.
11. **Autoscaling flapping:** Use a longer scale-in cooldown than scale-out.
12. **Tags and naming:** Apply them to *everything*. Graders will check.

---

## 10. Deliverables and Rubric Checklist

### Deliverables
- [ ] **Discovery report link** (what you found + business value)
- [ ] **Infrastructure repo link** (CloudFormation + GitSync deployment files)
- [ ] **Application repo link** (code, Dockerfile, workflow, appspec, taskdef)
- [ ] **Architecture diagram link** (VPC resources, delivery pipeline, numbered change flow)
- [ ] **Live review ready** (walkthrough, demos, defense)

### Rubric mapping

| Area | Weight | Maximize it by |
|---|---|---|
| Discovery report | **20%** | Sourced research, clear no-solution consequences, services mapped to stakeholder quotes |
| Solution | **50%** | Every mandatory requirement met and evidenced (use the traceability matrix) |
| Architecture diagram | **10%** | Shows VPC internals, endpoints, pipeline, and the flow of a change |
| Live review | **20%** | Smooth demos of every check; confident defense of cost and design trade-offs |

### Final pre-submission checklist
- [ ] Nothing created manually (apart from the documented CodeConnections handshake)
- [ ] Zero inline policies; zero long-lived credentials
- [ ] Tasks private, no NAT, no default route in private subnets
- [ ] Blue/green with auto-rollback proven with a deliberately bad release
- [ ] Scale-out and scale-in observed
- [ ] Single-task failure and AZ-loss behavior explained or demonstrated
- [ ] Cost explanation and rejected alternatives rehearsed
- [ ] READMEs let a new engineer rebuild everything from the repos
