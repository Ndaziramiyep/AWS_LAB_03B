# onward-orders-app

The Onward Logistics order system: a single Flask container that serves the UI and the order logic on port **8080**. Merging to `main` is the only step needed to release. GitHub Actions tests the code, builds the image, and pushes it to ECR with OIDC (no stored AWS keys). The ECR push triggers EventBridge, then CodePipeline, then a CodeDeploy blue/green release.

The infrastructure lives in **[onward-orders-infra](https://github.com/Ndaziramiyep/onward-orders-infra)**.

## Layout

| Path | Purpose |
|---|---|
| `app/main.py` | Routes: `/` (page), `/orders` (POST), `/health` (ALB check), `/version`, `/cpu` (load demo) |
| `app/settings.py` | Name, lab name, release note, and the `FORCE_UNHEALTHY` bad-release demo switch |
| `app/templates/index.html` | Page showing full name, lab name, version, task ID, and AZ |
| `tests/` | Unit tests that gate every build |
| `Dockerfile` | Multi-stage, slim base image, non-root user, gunicorn |
| `.github/workflows/build-push.yaml` | Test, then OIDC login, then push `:<sha>` and `:latest` |
| `appspec.yaml` | CodeDeploy AppSpec. `<TASK_DEFINITION>` is filled in by the pipeline. |
| `taskdef.json` | Task definition template. `<IMAGE1_NAME>` is replaced with the new image URI. |

`taskdef.json` is JSON because CodeDeploy registers it with the ECS `RegisterTaskDefinition` API. JSON has no comments, so the field notes are here:

- `family`: must match the CloudFormation bootstrap task definition.
- `executionRoleArn` / `taskRoleArn`: roles created by the `04-ecs` stack.
- `image: <IMAGE1_NAME>`: placeholder replaced by the pipeline.
- `awslogs-*`: the log group from the `04-ecs` stack.

## Run locally

```bash
docker build --build-arg APP_VERSION=local -t onward-orders:local .
docker run --rm -p 8080:8080 onward-orders:local
# open http://localhost:8080
```

Tests: `pip install -r app/requirements.txt pytest && pytest -q`

## Release demos

- **New version:** change `RELEASE_NOTE` in `app/settings.py`, then commit and push to `main`. The version (git SHA) on the page changes once CodeDeploy finishes.
- **Bad release and automatic rollback:** set `FORCE_UNHEALTHY = True` and push. The green tasks fail `/health`, the unhealthy-host alarm fires, and CodeDeploy rolls back. Set it back to `False` and push again.
- **Auto scaling:** `hey -z 3m -c 40 "http://<alb-dns>/cpu?seconds=1"`

## Security

No AWS secrets are stored in this repository or its settings. The role ARN in the workflow is not a secret. The role trusts only this repo's `main` branch and can only push to the `onward-orders-lab` ECR repository.
