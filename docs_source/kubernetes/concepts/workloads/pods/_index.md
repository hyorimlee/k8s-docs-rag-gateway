# Pods

Curated local excerpt derived from the official Kubernetes documentation for
retrieval experiments. Source: Kubernetes website, commit
`fe4bd876c5335ba137b1b564d93258c446b4b0ee`.

## Overview

Pods are the smallest deployable units of computing that you can create and
manage in Kubernetes. A Pod represents one or more application containers,
storage resources, a unique network identity, and options that govern how the
containers should run.

Pods are usually created and managed by workload resources such as Deployments,
Jobs, or CronJobs rather than created directly. Controllers create replacement
Pods when the desired state requires it.

## Workload Boundary

Pods are intended to run application containers together when those containers
need to share networking, storage, or lifecycle. They are not durable identity
objects for an application. If a Pod fails or is deleted, a controller may
create a different Pod to replace it.

## Retrieval Notes

Useful retrieval terms: pod, pods, workload, deployment, job, cronjob,
controller, container, network, storage, lifecycle.
