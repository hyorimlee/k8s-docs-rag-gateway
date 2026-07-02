# CronJob Backfill Safety Checklist

This is a generic portfolio runbook. It does not describe any private cluster, company environment, IP address, credential, kubeconfig file, or internal service.

## Purpose

Use this checklist to shape safe, documentation-grounded answers about backfilling work that is normally scheduled by a Kubernetes CronJob.

## Safe Planning Flow

1. Confirm the intended time range and avoid duplicate processing.
2. Review whether the CronJob allows concurrent runs.
3. Check the Job template and expected runtime before creating backfill Jobs.
4. Consider idempotency and whether repeated execution is safe.
5. Consider downstream load, rate limits, and external side effects in general terms.
6. Use clear labels or annotations for manually created backfill Jobs.
7. Monitor completion and failure status after backfill Jobs are created.
8. Avoid recommending deletion or forced restart as a first step.

## Assistant Boundary

The assistant should not create commands for a specific private environment unless the user supplies safe, non-secret examples. It should avoid inventing cluster names, namespaces, schedules, credentials, or service names.
