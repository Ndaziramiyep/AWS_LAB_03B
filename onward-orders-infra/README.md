# onward-orders-infra

Infrastructure for the Onward Logistics order system. Everything is defined in **CloudFormation** and deployed through **CloudFormation GitSync**. Nothing is created by hand in the console, apart from the one-time GitHub authorization for the CodeConnections connection.

Application code, Dockerfile, CI workflow, `appspec.yaml`, and `taskdef.json` live in the separate repo **[onward-orders-app](https://github.com/Ndaziramiyep/onward-orders-app)**.

## How the pieces fit

```
merge to main ─► GitHub Actions (OIDC, no keys) ─► ECR :<sha> + :latest
                                                     │ "ECR Image Action: PUSH latest"
                                                     ▼
                                   EventBridge ─► CodePipeline ─► CodeDeploy blue/green
                                                                    │ canary 10% → 100%
Internet ─► ALB (public subnets) ─► blue / green target groups ─► Fargate tasks (private subnets)
                                                                    │ no 0.0.0.0/0, no NAT
                                              VPC endpoints: ecr.api, ecr.dkr, logs (interface), s3 (gateway)
```

Full diagram with the numbered change flow: [docs/architecture.md](docs/architecture.md). Costs: [docs/cost-analysis.md](docs/cost-analysis.md). Discovery report: [docs/discovery-report.md](docs/discovery-report.md).

## Layout

| Path | Purpose |
|---|---|
| `bootstrap/00-gitsync-role.yaml` | GitSync/CloudFormation role and GitHub connection. The only stack deployed with the CLI, because GitSync needs this role before it can run. |
| `templates/01-foundation.yaml` | GitHub OIDC provider, GitHub Actions role (ECR push only, `main` branch only), ECR repo |
| `templates/02-network.yaml` | VPC, 2 public + 2 private subnets in 2 AZs, chained SGs, VPC endpoints. No NAT. |
| `templates/03-alb.yaml` | Internet-facing ALB, prod listener (:80) and test listener (:8080), blue and green target groups |
| `templates/04-ecs.yaml` | Cluster, log group, task roles, bootstrap task definition, ECS service (`CODE_DEPLOY` controller) |
| `templates/05-autoscaling.yaml` | Target tracking on CPU (55%) and memory (75%), 2 to 6 tasks, optional overnight scale-to-zero |
| `templates/06-delivery.yaml` | Artifact bucket, rollback alarms, CodeDeploy app/group, CodePipeline, EventBridge rule |
| `deployments/*.deployment.yaml` | One GitSync deployment file per stack: parameters + company tags |
| `rules/onward-standards.guard` | cfn-guard rules: no inline policies, no NAT, private tasks, encrypted buckets |
| `scripts/gitsync-setup.sh` | Creates the GitSync configs in order and waits for each stack |
| `scripts/teardown.sh` | Deletes all stacks in reverse order (idle environment = no cost) |

## Company standards

- **Naming:** `<project>-<environment>-<resource>`, for example `onward-orders-lab-alb`. Set once with the `ResourcePrefix` parameter.
- **Tags:** applied by GitSync from each deployment file to the stack, and propagated to every taggable resource: `Project`, `Environment`, `Owner`, `CostCenter`, `ManagedBy`, `Repository`. Every resource also gets a `Name` tag.
- **IAM:** no inline policies. Roles use `ManagedPolicyArns` with `AWS::IAM::ManagedPolicy` or AWS-managed policies. CI checks this with `grep` and cfn-guard.

## Rebuild from scratch

Region `eu-west-1`, account `648637468459`. Run from the repo root with admin credentials.

1. **Bootstrap (once).** This stack creates the role GitSync uses, so it cannot deploy itself:
   ```bash
   aws cloudformation deploy --region eu-west-1 \
     --stack-name onward-orders-lab-00-bootstrap \
     --template-file bootstrap/00-gitsync-role.yaml \
     --capabilities CAPABILITY_NAMED_IAM \
     --parameter-overrides ExistingConnectionArn=arn:aws:codeconnections:eu-west-1:648637468459:connection/387b1181-82b8-4718-b249-b81bfe30c3c0 \
     --tags Project=onward-orders Environment=lab Owner=patrick-ndaziramiye CostCenter=amalitech-training ManagedBy=cloudformation Repository=onward-orders-infra
   ```
   If `ExistingConnectionArn` is left empty, a new connection is created in `PENDING` status. Open **Developer Tools > Settings > Connections** and click **Update pending connection** to authorize GitHub. This is the only manual console step.
2. **Foundation, network, ALB** through GitSync:
   ```bash
   ./scripts/gitsync-setup.sh 01-foundation 02-network 03-alb
   ```
3. **First image.** In the app repo, push to `main`. GitHub Actions builds and pushes `:<sha>` and `:latest`. The tasks run in private subnets with no internet path, so the image must be in ECR before the service exists.
4. **ECS, autoscaling, delivery** through GitSync:
   ```bash
   ./scripts/gitsync-setup.sh 04-ecs 05-autoscaling 06-delivery
   ```
5. Open the `LoadBalancerDnsName` output of the `03-alb` stack in a browser.

After this, any change to a template or deployment file merged to `main` updates its own stack automatically.

**About the first pipeline run:** the delivery stack is created after the first image push, so that push does not trigger a pipeline. The service is already running that image from the bootstrap task definition. Every later push goes through the pipeline. To prove the pipeline end to end right away, release it once with `aws codepipeline start-pipeline-execution --name onward-orders-lab-pipeline`.

## Release, rollback, and idle

- **Release:** merge to `main` in the app repo. Nothing else. CodeDeploy shifts 10% of traffic to the new version for 5 minutes, then 100%. The old tasks stay up for 5 more minutes as the rollback window.
- **Automatic rollback:** if `onward-orders-lab-alb-target-5xx` or either `tg-*-unhealthy` alarm fires, or the deployment fails, CodeDeploy reverts traffic to the old tasks.
- **Manual rollback during a release:** `aws deploy stop-deployment --deployment-id <id> --auto-rollback-enabled`, or **Stop and roll back** in the CodeDeploy console.
- **Roll back to an older version after a release finished:** re-tag the earlier SHA as `latest`. That push triggers the pipeline with the old image:
  ```bash
  MANIFEST=$(aws ecr batch-get-image --repository-name onward-orders-lab --image-ids imageTag=<old-sha> --query 'images[0].imageManifest' --output text)
  aws ecr put-image --repository-name onward-orders-lab --image-tag latest --image-manifest "$MANIFEST"
  ```
- **Idle (Finance):** `./scripts/teardown.sh` removes every billable resource, and steps 2 to 4 rebuild it. For nights only, set `EnableOfficeHoursSchedule: "true"` in `deployments/05-autoscaling.deployment.yaml`. That removes Fargate cost only. The ALB and endpoints still bill.

## Things a new engineer must know

1. **CodeDeploy owns the service after creation.** Do not change `TaskDefinition` or `LoadBalancers` in `04-ecs.yaml`, or the listener default actions in `03-alb.yaml`. After a release, production may point at the *green* group, and a stack update would fight CodeDeploy. Ship app changes through the app repo.
2. **Stack order matters.** GitSync has no cross-stack ordering. Stacks share values with `Export`/`ImportValue` named `onward-orders-lab-*`. Create them 01 to 06 and delete them in reverse.
3. **Tasks stuck in PROVISIONING or `CannotPullContainerError`** almost always means a missing endpoint (`ecr.api`, `ecr.dkr`, `logs`, S3 gateway) or `endpoint-sg` not allowing 443 from `task-sg`.
4. **ECR tags:** SHA tags are immutable. Only `latest` can move (`IMMUTABLE_WITH_EXCLUSION`), because `latest` is what the pipeline watches.

## Live demo checklist

| Check | How |
|---|---|
| One public address, private tasks | Open the ALB DNS. ECS task > Networking shows no public IP. VPC > Route tables `private-rt-a/b` have only `local` and the S3 prefix list. |
| Push → live, no human | Edit `RELEASE_NOTE` in `app/settings.py`, push. Watch Actions > ECR > CodePipeline > CodeDeploy. |
| Zero downtime | `while true; do curl -s http://<alb>/version; echo; sleep 1; done` during the release. Every line succeeds, and the version flips. |
| Bad release rolls back | Set `FORCE_UNHEALTHY = True`, push. Green tasks fail `/health`, the unhealthy alarm fires, CodeDeploy rolls back. Blue keeps serving. Set it back to `False` afterwards. |
| No long-lived credentials | GitHub > Settings > Secrets is empty. IAM > Users has no keys. Show the OIDC trust on `onward-orders-lab-github-actions-role`. |
| Scale out and in | `hey -z 3m -c 40 "http://<alb>/cpu?seconds=1"`, then watch the desired count rise and fall after the 300 s cooldown. |
| Task failure | `aws ecs stop-task --cluster onward-orders-lab-cluster --task <id>`. The ALB keeps serving and ECS replaces the task. |
| AZ loss | The home page shows the AZ. Refresh to see both `eu-west-1a` and `eu-west-1b`. Stopping every task in one AZ leaves the other serving. |
