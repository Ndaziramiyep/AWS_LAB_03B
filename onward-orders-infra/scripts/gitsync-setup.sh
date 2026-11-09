#!/usr/bin/env bash
# Creates the CloudFormation GitSync configuration for each stack, IN ORDER, and waits for each
# stack to finish before starting the next (GitSync has no cross-stack ordering).
# Usage:  ./scripts/gitsync-setup.sh 01-foundation 02-network 03-alb
#         (push the first image from the app repo)
#         ./scripts/gitsync-setup.sh 04-ecs 05-autoscaling 06-delivery
set -euo pipefail                                         # Stop on any error, unset var, or pipe failure

REGION="${AWS_REGION:-eu-west-1}"                         # Target region
PREFIX="${PREFIX:-onward-orders-lab}"                     # Naming prefix (matches templates)
OWNER="${GITHUB_OWNER:-Ndaziramiyep}"                     # GitHub account that owns the infra repo
REPO="${INFRA_REPO:-onward-orders-infra}"                 # Infra repo name
BRANCH="${BRANCH:-main}"                                  # Branch GitSync follows
BOOTSTRAP_STACK="${PREFIX}-00-bootstrap"                  # Name of the one-time bootstrap stack

out() {                                                   # Reads one output value from the bootstrap stack
  aws cloudformation describe-stacks --region "$REGION" --stack-name "$BOOTSTRAP_STACK" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
}

ROLE_ARN="$(out GitSyncRoleArn)"                          # Role GitSync assumes
CONNECTION_ARN="$(out ConnectionArn)"                     # GitHub connection
echo "GitSync role:  $ROLE_ARN"                           # Show what will be used
echo "Connection:    $CONNECTION_ARN"                     # Show what will be used

LINK_ID="$(aws codeconnections list-repository-links --region "$REGION" \
  --query "RepositoryLinks[?OwnerId=='$OWNER' && RepositoryName=='$REPO'].RepositoryLinkId | [0]" --output text)"  # Existing link, if any
if [[ -z "$LINK_ID" || "$LINK_ID" == "None" ]]; then      # No link yet
  LINK_ID="$(aws codeconnections create-repository-link --region "$REGION" \
    --connection-arn "$CONNECTION_ARN" --owner-id "$OWNER" --repository-name "$REPO" \
    --query RepositoryLinkInfo.RepositoryLinkId --output text)"  # Link the infra repo to AWS once
fi
echo "Repository link: $LINK_ID"                          # Show the link ID

for NAME in "$@"; do                                      # Each stack passed on the command line, in order
  STACK="${PREFIX}-${NAME}"                               # Stack name, e.g. onward-orders-lab-02-network
  FILE="deployments/${NAME}.deployment.yaml"              # Its GitSync deployment file
  [[ -f "$FILE" ]] || { echo "Missing $FILE"; exit 1; }   # Fail fast on typos
  if aws codeconnections get-sync-configuration --region "$REGION" \
       --sync-type CFN_STACK_SYNC --resource-name "$STACK" >/dev/null 2>&1; then  # Already configured?
    echo "Sync configuration for $STACK already exists"   # Skip creation
  else
    echo "Creating sync configuration for $STACK"         # Create it
    aws codeconnections create-sync-configuration --region "$REGION" \
      --branch "$BRANCH" \
      --config-file "$FILE" \
      --repository-link-id "$LINK_ID" \
      --resource-name "$STACK" \
      --role-arn "$ROLE_ARN" \
      --sync-type CFN_STACK_SYNC \
      --publish-deployment-status ENABLED \
      --trigger-resource-update-on FILE_CHANGE >/dev/null  # Update only when this stack's files change
  fi
  echo "Waiting for $STACK ..."                           # GitSync creates the stack asynchronously
  for _ in $(seq 1 120); do                               # Up to ~30 minutes
    STATUS="$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$STACK" \
      --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo PENDING)"  # Current status
    case "$STATUS" in
      CREATE_COMPLETE|UPDATE_COMPLETE) echo "$STACK: $STATUS"; break ;;          # Done, next stack
      *FAILED|*ROLLBACK_COMPLETE) echo "$STACK: $STATUS - check stack events"; exit 1 ;;  # Stop on failure
      *) sleep 15 ;;                                      # Still working
    esac
  done
done
