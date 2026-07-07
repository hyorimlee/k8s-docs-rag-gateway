# Secrets

Curated local excerpt derived from the official Kubernetes documentation for
retrieval experiments. Source: Kubernetes website, commit
`fe4bd876c5335ba137b1b564d93258c446b4b0ee`.

## Overview

A Secret is an object that contains a small amount of sensitive data such as a
password, token, or key. Using a Secret means sensitive data does not need to be
included directly in a Pod specification or container image.

## Handling Sensitive Data

Secrets reduce accidental exposure compared with embedding sensitive values in
plain manifests, but they still require careful access control and handling.
Applications can consume Secrets through environment variables or mounted files.

## Assistant Boundary

Avoid asking users to paste raw Secrets, API keys, kubeconfig files, private
keys, or credentials into chat. If secret-related troubleshooting is needed, ask for
redacted metadata or configuration shape instead of secret values.

## Retrieval Notes

Useful retrieval terms: secret, secrets, sensitive data, password, token, key,
api key, credentials, environment variable, volume, redacted.
