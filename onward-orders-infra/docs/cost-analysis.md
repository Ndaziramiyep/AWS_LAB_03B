# Cost analysis: Onward Orders (lab environment)

Region **eu-west-1 (Ireland)**, 730 hours per month, approximate on-demand list prices. Check them in the [AWS Pricing Calculator](https://calculator.aws/) before you quote them.

## Monthly running cost (always on, 2 tasks)

| Component | Basis | Approx. per month | Idle cost? |
|---|---|---|---|
| Fargate | 2 tasks × (0.25 vCPU × $0.04048 + 0.5 GB × $0.004445) per hour | **~$18** | Only while tasks run |
| ALB | $0.0252/hour + LCUs (lab traffic < 1 LCU, $0.008 per LCU-hour) | **~$24** | Yes |
| Interface endpoints | 3 endpoints (`ecr.api`, `ecr.dkr`, `logs`) × 2 AZs × $0.011/hour | **~$48** | Yes |
| Endpoint data | $0.01/GB processed (image pulls + logs, < 5 GB) | < $1 | No |
| S3 gateway endpoint | Free | $0 | No |
| ECR | $0.10/GB-month, ~20 images × ~60 MB | ~$0.12 | Small |
| CodePipeline V2 | $0.002 per action-minute, first 100 min/month free | ~$0 | No |
| CodeDeploy (ECS) | No charge | $0 | No |
| CloudWatch | Logs (14-day retention), 3 alarms × $0.10, Container Insights | ~$3 | Small |
| **Total** | | **~$94/month** | |

At peak, the service scales to 6 tasks. That adds about $9 per extra task-month, only for the hours those tasks run.

## Private connectivity: endpoints vs NAT

| | 3 interface endpoints × 2 AZs | 1 NAT gateway | 2 NAT gateways (HA) |
|---|---|---|---|
| Fixed | ~$48 | ~$35 ($0.048/hour) | ~$70 |
| Per GB | $0.01 | $0.048 | $0.048 |
| Internet path for the app | **None** | Yes | Yes |
| Meets the Head of Security's requirement | **Yes** | No | No |

**Position:** the endpoints cost about $13/month more than a single NAT gateway, but less than an HA pair. They are the only option that meets the requirement that the application has no internet path. They also process data at about a fifth of the NAT per-GB price, and their policies control which AWS services the tasks can reach.

**Cost levers:**
- Use only the three endpoints Fargate needs.
- Use the free S3 gateway endpoint, not an S3 interface endpoint.
- Keep log retention at 14 days.
- Tear down environments when they are idle.

## "Idle environments should not cost money"

| Option | How | What still bills |
|---|---|---|
| **Teardown** (chosen for nights and weekends of the lab) | `scripts/teardown.sh` deletes stacks 06 to 01. Rebuild with `scripts/gitsync-setup.sh`. | Nothing except ECR images (deleted too, since `EmptyOnDelete`) and the bootstrap IAM role, which is free |
| Scale to zero | `MinCapacity: "0"`, `MaxCapacity: "0"`, or `EnableOfficeHoursSchedule: "true"` | ALB + endpoints, ~$72/month. This saves Fargate only. |

## Sizing justification

- **0.25 vCPU / 512 MiB** per task: the smallest Fargate size. Gunicorn with 2 workers and 4 threads uses about 120 MiB. Capacity grows by adding tasks (horizontal), which also adds AZ redundancy. Bigger tasks would not add redundancy.
- **Minimum 2 tasks:** one per AZ, so the service survives a task failure or an AZ loss.
- **Maximum 6 tasks:** a cost ceiling for peak days of about 3× normal load.

## Rejected alternatives

| Alternative | Why rejected |
|---|---|
| NAT gateway instead of endpoints | Gives the app an internet path, which Security forbids. Its per-GB price is about 5× higher. |
| ECS rolling update (no CodeDeploy) | No test listener, no canary traffic shifting, no alarm-driven rollback |
| EC2 launch type | Patching and capacity management burden. Fargate removes it. |
| IAM user keys in GitHub secrets | Long-lived credentials, which Security forbids. OIDC gives 1-hour STS credentials instead. |
| Tasks in public subnets | Puts the application on the internet |
| Console or Terraform | The requirement is CloudFormation + GitSync |
| Nested stacks | GitSync does not upload child templates. Separate stacks with exports are simpler. |
| Elastic Beanstalk / App Runner | Less control over networking and the required pipeline components |
| Single AZ | Fails the AZ-loss requirement |
