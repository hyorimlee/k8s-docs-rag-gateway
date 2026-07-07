# Jobs

Curated local excerpt derived from the official Kubernetes documentation for
retrieval experiments. Source: Kubernetes website, commit
`fe4bd876c5335ba137b1b564d93258c446b4b0ee`.

## Overview

A Job creates one or more Pods and continues retrying execution until the
specified number of successful completions is reached. Jobs are useful for
finite work such as batch processing, data migration, or one-off tasks.

## Completion and Retry

Jobs track successful completions and failed Pods. Depending on the Job
configuration, Kubernetes may retry failed Pods. A Job differs from a Deployment
because the desired outcome is completion rather than continuously running
replicas.

## Batch Workload Safety

Before creating replacement or backfill Jobs, review whether the workload is
idempotent, whether duplicate processing is safe, and whether parallelism or
retry policy could create unexpected repeated work.

## Retrieval Notes

Useful retrieval terms: job, jobs, batch, completions, retries, backoff,
parallelism, pod, cronjob, backfill.
