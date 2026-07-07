# Pod Lifecycle

Curated local excerpt derived from the official Kubernetes documentation for
retrieval experiments. Source: Kubernetes website, commit
`fe4bd876c5335ba137b1b564d93258c446b4b0ee`.

## Pod Phase

A Pod's `status` field includes a `phase`. Common phases include `Pending`,
`Running`, `Succeeded`, `Failed`, and `Unknown`.

`Pending` means the Pod has been accepted by the Kubernetes cluster, but one or
more containers have not been set up and made ready to run. This can include the
time before the Pod is scheduled as well as time spent downloading container
images.

## Conditions and Container State

Pod status also includes conditions and per-container state. These fields help
separate scheduling progress, container startup, readiness, termination, and
failure reasons.

## Troubleshooting Boundary

For a Pending Pod, useful documentation-grounded checks include scheduling
constraints, resource requests, image pull progress, node availability, taints,
tolerations, affinity, and events. This local gateway does not inspect a live
cluster and should not invent event messages, node names, namespaces, or pod
names.

## Retrieval Notes

Useful retrieval terms: pod lifecycle, pending, running, succeeded, failed,
unknown, conditions, container state, scheduling, image pull, troubleshooting.
