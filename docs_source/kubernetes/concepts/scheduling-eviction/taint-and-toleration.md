# Taints and Tolerations

Curated local excerpt derived from the official Kubernetes documentation for
retrieval experiments. Source: Kubernetes website, commit
`fe4bd876c5335ba137b1b564d93258c446b4b0ee`.

## Overview

Taints allow a node to repel Pods. Tolerations allow a Pod to be scheduled onto
a node with matching taints. Taints and tolerations work together to control
which Pods can use which nodes.

## Scheduling Effects

Common taint effects include `NoSchedule`, `PreferNoSchedule`, and `NoExecute`.
If a Pod does not tolerate a relevant taint, it may remain unscheduled. This is
a common area to check when a Pod is Pending.

## Safe Triage

For scheduling issues, compare node taints with Pod tolerations. Avoid
recommending workload deletion as a first step; first confirm whether taints and
tolerations explain placement.

## Retrieval Notes

Useful retrieval terms: taint, taints, toleration, tolerations, NoSchedule,
PreferNoSchedule, NoExecute, scheduling, pending.
