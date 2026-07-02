# Pod Pending Troubleshooting Checklist

This is a generic portfolio runbook. It does not describe any private cluster, company environment, IP address, credential, kubeconfig file, or internal service.

## Purpose

Use this checklist to shape documentation-grounded answers for Pods that remain in the `Pending` phase.

## Safe Triage Flow

1. Confirm that the question is asking for general Kubernetes guidance, not live cluster inspection.
2. Explain that a Pending Pod often indicates that it has not been scheduled or cannot start with the requested constraints.
3. Check whether resource requests fit available node capacity.
4. Check node selectors, node affinity, and required placement rules.
5. Check taints on candidate nodes and whether the Pod has matching tolerations.
6. Check whether namespace quota or limit ranges could block the workload.
7. Check whether referenced configuration objects exist, such as ConfigMaps and Secrets.
8. Recommend reviewing Kubernetes Events and scheduler messages without claiming to access them directly.

## Assistant Boundary

The assistant should not claim to see the user's cluster, Pods, Nodes, Events, logs, or metrics. It should provide a safe checklist and cite retrieved Kubernetes documentation when available.
