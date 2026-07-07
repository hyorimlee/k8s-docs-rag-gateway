# Resource Management for Pods and Containers

Curated local excerpt derived from the official Kubernetes documentation for
retrieval experiments. Source: Kubernetes website, commit
`fe4bd876c5335ba137b1b564d93258c446b4b0ee`.

## Overview

Containers can specify resource requests and resource limits. Requests describe
the amount of CPU or memory Kubernetes should reserve for scheduling. Limits
describe the maximum amount a container is allowed to use.

## Scheduling and Capacity

The scheduler uses resource requests when deciding whether a Pod can fit on a
node. If requested resources cannot fit available node capacity, a Pod can stay
Pending.

## Safe Triage

For a Pending Pod, compare CPU and memory requests with node allocatable
capacity. Avoid destructive actions until you understand whether capacity,
requests, limits, quotas, or placement constraints explain the scheduling
result.

## Retrieval Notes

Useful retrieval terms: resources, resource requests, resource limits, CPU,
memory, scheduling, capacity, allocatable, pending.
