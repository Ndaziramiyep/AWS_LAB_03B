# Discovery report: safe order system delivery for Onward Logistics

**Author:** Patrick Ndaziramiye | **Lab:** Delivering Order System Updates Safely

> The stakeholder lines below summarise the client brief. Replace them with the exact quotes from the *Client Profile: Onward Logistics* before you submit.

## Part A: What I found

### How teams usually deliver changes

| Approach | How it works | Strength | Weakness for Onward |
|---|---|---|---|
| Manual deploys (SSH, console) | An engineer copies files and restarts the app | No tooling needed | Slow, error-prone, needs standing credentials, no audit trail |
| Scripts / cron | Shell scripts run the steps | Repeatable | Brittle, still needs keys, no traffic control |
| Rolling update (ECS default) | Tasks are replaced a few at a time | Built in, no extra cost | Old and new versions serve together, no test listener, rollback is another rollout |
| **Blue/green** | A full new copy starts beside the old one, then traffic switches | Instant switch back, test before going live | Briefly runs two copies |
| **Canary / linear** | A small share of traffic goes to the new version first | Limits how many users a bad release reaches | Needs health signals (alarms) |
| Jenkins / GitLab CI | Self-hosted or SaaS CI/CD servers | Flexible | Servers to patch, often long-lived cloud keys |
| ECS native blue/green, App Runner, Elastic Beanstalk | Managed release features | Less to build | Less control over the networking and pipeline the brief requires |

### What happens with no solution

- **Downtime on release.** Customers placing orders get errors, and peak days are the riskiest.
- **Slow, inconsistent releases.** Manual steps differ per engineer, and environments drift apart.
- **Credential leakage.** Long-lived access keys in laptops or CI secrets are a leading cause of cloud breaches.
- **No fast rollback.** Reverting means another manual deploy under pressure.
- **Release fear.** Teams batch changes and ship less often, which makes each release riskier.

### Sources

1. AWS Well-Architected Framework, Operational Excellence pillar: *OPS06 "Mitigate deployment risks"*. https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/
2. AWS Whitepaper: *Blue/Green Deployments on AWS*. https://docs.aws.amazon.com/whitepapers/latest/blue-green-deployments/
3. Amazon ECS Developer Guide: *Blue/green deployment with CodeDeploy*. https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-type-bluegreen.html
4. AWS CodeDeploy User Guide: *Deployment configurations on an Amazon ECS compute platform*. https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-configurations.html
5. GitHub Docs: *Configuring OpenID Connect in Amazon Web Services*. https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services
6. Amazon ECR User Guide: *Amazon ECR interface VPC endpoints (AWS PrivateLink)*. https://docs.aws.amazon.com/AmazonECR/latest/userguide/vpc-endpoints.html
7. AWS CloudFormation User Guide: *Git sync*. https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/git-sync.html
8. AWS Well-Architected Security pillar: *SEC02 "Use temporary credentials"*. https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/

## Part B: Business value

### Chosen approach

ECS Fargate in private subnets behind one ALB. GitHub Actions (OIDC) pushes to ECR, then EventBridge, CodePipeline, and CodeDeploy blue/green (canary 10% for 5 minutes) release with alarm-based auto rollback. All infrastructure is CloudFormation deployed by GitSync. AWS access goes through VPC endpoints, with no NAT gateway.

### Services and why

| Service | Why | Stakeholder need it answers |
|---|---|---|
| Application Load Balancer | Single public entry point. Health checks. Two listeners for blue/green. | Security: "one public entry point". CTO: "no outage on release". |
| ECS on Fargate | No servers to patch. Tasks spread over 2 AZs. | Operations: "survive container or AZ failure". |
| Application Auto Scaling | Target tracking on CPU/memory, 2 to 6 tasks | Operations: "scale without manual action" |
| Amazon ECR | Private registry, scan on push, immutable SHA tags | Security, plus fast rollback to any earlier SHA |
| VPC endpoints (ecr.api, ecr.dkr, logs, S3 gateway) | AWS access without any internet route | Security: "app has no internet path" |
| GitHub Actions + IAM OIDC | Builds with 1-hour STS credentials. No stored keys. | Security: "no long-lived credentials" |
| EventBridge | Event-driven trigger on image push. No polling. | CTO: "merge is the only manual step" |
| CodePipeline + CodeDeploy | Managed blue/green, canary shift, auto rollback on alarms | CTO: "no outage, fast rollback" |
| CloudWatch alarms | 5XX and unhealthy-host signals stop bad releases | CTO and Operations |
| CloudFormation GitSync | Every change reviewed in Git and applied automatically. Rebuildable. | CTO: "readable for new engineers". Finance: "tear down when idle". |

### Who benefits

- **Customers:** no outage during releases, and bad releases reach at most 10% of traffic for minutes.
- **CTO:** merging is the whole release process. Releases are frequent and boring.
- **Head of Security:** no keys to leak, one public door, and the application cannot reach the internet.
- **Head of Operations:** self-healing tasks across 2 AZs, automatic scaling, alarms.
- **Finance Lead:** pay-per-second Fargate, teardown or scale-to-zero when idle, and a clear endpoint cost (see [cost-analysis.md](cost-analysis.md)).
- **Engineers:** two small, documented repos, and the same environment rebuilt from code every time.
