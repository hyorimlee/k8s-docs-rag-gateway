# ConfigMaps

Curated local excerpt derived from the official Kubernetes documentation for
retrieval experiments. Source: Kubernetes website, commit
`fe4bd876c5335ba137b1b564d93258c446b4b0ee`.

## Overview

A ConfigMap is an API object used to store non-confidential data in key-value
pairs. Pods can consume ConfigMaps as environment variables, command-line
arguments, or files in a volume.

## Configuration Boundary

ConfigMaps are intended for non-sensitive configuration. They help separate
configuration data from container images and application code.

## Secret Boundary

Avoid using ConfigMaps for passwords, tokens, private keys, or other sensitive
values. Use Secret objects for sensitive data, and avoid exposing raw secrets in
chat, traces, logs, or examples.

## Retrieval Notes

Useful retrieval terms: configmap, configmaps, configuration, key-value,
environment variable, volume, non-sensitive data, secret boundary.
