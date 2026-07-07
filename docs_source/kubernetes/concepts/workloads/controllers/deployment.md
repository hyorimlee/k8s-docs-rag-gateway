# Deployments

Curated local excerpt derived from the official Kubernetes documentation for
retrieval experiments. Source: Kubernetes website, commit
`fe4bd876c5335ba137b1b564d93258c446b4b0ee`.

## Overview

A Deployment manages a set of replicated Pods and provides declarative updates
for applications. Deployments work with ReplicaSets to keep the desired number
of Pods available.

## Rollout Behavior

When a Deployment's Pod template changes, Kubernetes can roll out the new
template while managing availability. Deployment status and rollout history help
explain whether the desired state is progressing.

## Workload Use

Deployments are commonly used for long-running stateless applications. They are
different from Jobs and CronJobs, which focus on finite or scheduled batch work.

## Retrieval Notes

Useful retrieval terms: deployment, deployments, rollout, replicas, replicaset,
pod template, workload, stateless.
