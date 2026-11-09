#!/usr/bin/env bash
# Deletes the whole environment in REVERSE order so an idle environment costs nothing.
# Everything is rebuildable from the two repos (see README "Rebuild from scratch").
# Usage: ./scripts/teardown.sh            (keeps the 00 bootstrap stack and GitHub connection)
#        KEEP_BOOTSTRAP=false ./scripts/teardown.sh   (removes it too)
set -euo pipefail                                         # Stop on any error

REGION="${AWS_REGION:-eu-west-1}"                         # Target region
PREFIX="${PREFIX:-onward-orders-lab}"                     # Naming prefix
STACKS=(06-delivery 05-autoscaling 04-ecs 03-alb 02-network 01-foundation)  # Reverse creation order

for NAME in "${STACKS[@]}"; do                            # Each stack, newest first
  STACK="${PREFIX}-${NAME}"                               # Full stack name
  aws codeconnections delete-sync-configuration --region "$REGION" \
    --sync-type CFN_STACK_SYNC --resource-name "$STACK" 2>/dev/null || true  # Stop GitSync re-creating it
  if [[ "$NAME" == "06-delivery" ]]; then                 # Versioned artifact bucket must be emptied first
    BUCKET="${PREFIX}-artifacts-$(aws sts get-caller-identity --query Account --output text)-${REGION}"  # Bucket name
    python - "$BUCKET" "$REGION" <<'PY' 2>/dev/null || true
import sys, boto3                                         # AWS SDK for Python
b = boto3.resource("s3", region_name=sys.argv[2]).Bucket(sys.argv[1])  # The artifact bucket
b.object_versions.delete()                                # Delete every object version
PY
  fi
  echo "Deleting $STACK"                                  # Progress
  aws cloudformation delete-stack --region "$REGION" --stack-name "$STACK"  # Start delete
  aws cloudformation wait stack-delete-complete --region "$REGION" --stack-name "$STACK"  # Wait until gone
done

if [[ "${KEEP_BOOTSTRAP:-true}" == "false" ]]; then       # Optional full clean-up
  aws cloudformation delete-stack --region "$REGION" --stack-name "${PREFIX}-00-bootstrap"  # Delete bootstrap
  aws cloudformation wait stack-delete-complete --region "$REGION" --stack-name "${PREFIX}-00-bootstrap"  # Wait
fi
echo "Teardown complete. ALB, endpoints and Fargate no longer bill."  # Done
