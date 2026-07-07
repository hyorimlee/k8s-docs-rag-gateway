# Assigning Pods to Nodes

Curated local excerpt derived from the official Kubernetes documentation for
retrieval experiments. Source: Kubernetes website, commit
`fe4bd876c5335ba137b1b564d93258c446b4b0ee`.

## Overview

Kubernetes normally schedules Pods onto nodes automatically. Users can influence
placement with fields such as `nodeSelector`, node affinity, pod affinity, pod
anti-affinity, and topology spread constraints.

## Scheduling Constraints

Hard placement constraints can prevent a Pod from being scheduled if no node
matches. Soft preferences influence scheduling without requiring an exact
match. For Pending Pods, placement rules are a key diagnostic area.

## Safe Triage

When troubleshooting scheduling, compare Pod placement requirements with node
labels and available nodes. Avoid assuming a specific node or namespace exists
unless it is provided by the user.

## Retrieval Notes

Useful retrieval terms: scheduling, assign pod to node, nodeSelector, node
affinity, pod affinity, anti-affinity, topology spread, pending.
