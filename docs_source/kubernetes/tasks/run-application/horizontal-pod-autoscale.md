# Horizontal Pod Autoscaling

Curated local excerpt derived from the official Kubernetes documentation for
retrieval experiments. Source: Kubernetes website, commit
`fe4bd876c5335ba137b1b564d93258c446b4b0ee`.

## Overview

Horizontal Pod Autoscaling automatically updates a workload resource, such as a
Deployment or ReplicaSet, with the goal of matching demand. The Horizontal Pod
Autoscaler changes the number of Pod replicas rather than changing resources on
an individual Pod.

## Metrics

Horizontal Pod Autoscaling can use metrics such as CPU utilization, memory, or
custom metrics when the required metrics pipeline is available. The controller
compares current metrics with the configured target and adjusts replica count.

## Capacity Boundary

Autoscaling does not inspect application correctness and does not replace
capacity planning. If the cluster has insufficient nodes or resources, adding
replicas may not make Pods schedulable.

## Retrieval Notes

Useful retrieval terms: horizontal pod autoscaler, hpa, autoscaling, metrics,
cpu utilization, memory, custom metrics, replicas, deployment, capacity.
