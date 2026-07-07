# CronJobs

Curated local excerpt derived from the official Kubernetes documentation for
retrieval experiments. Source: Kubernetes website, commit
`fe4bd876c5335ba137b1b564d93258c446b4b0ee`.

## Overview

A CronJob creates Jobs on a repeating schedule. It is useful for periodic and
recurring tasks such as backups, reports, cleanup jobs, or scheduled batch
workloads.

## Schedule and Job Creation

The CronJob schedule uses cron syntax. At each scheduled time, the controller
creates a Job from the job template if policy and timing constraints allow it.

## Concurrency and Missed Runs

CronJobs include settings that affect repeated or overlapping execution, such as
concurrency policy, starting deadline, successful job history, and failed job
history. These settings matter for backfill planning because missed or repeated
runs can produce duplicate work.

## Retrieval Notes

Useful retrieval terms: cronjob, cronjobs, schedule, job template, concurrency
policy, missed run, backfill, batch.
