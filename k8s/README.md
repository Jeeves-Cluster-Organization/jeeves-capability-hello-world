# Kubernetes Deployment Manifests

**Parent:** [README.md](../README.md)

---

## Overview

This directory contains Kubernetes manifests for deploying the Jeeves Hello World capability. The manifests are organized using Kustomize for easy customization across environments.

## Directory Structure

```
k8s/
├── README.md                 # This file
├── base/                     # Single-node deployment (development)
│   ├── kustomization.yaml
│   ├── deployment.yaml       # Orchestrator + LLM server
│   ├── service.yaml          # ClusterIP services
│   └── configmap.yaml        # Configuration
└── overlays/
    └── distributed/          # Multi-node deployment (production)
        ├── kustomization.yaml
        ├── patch-disable-single-node.yaml
        ├── node1-deployment.yaml  # understand, think, respond
        ├── node2-deployment.yaml  # (reserved for future)
        └── node3-deployment.yaml  # (reserved for future)
```

---

## Deployment Modes

### Single-Node (Development)

All 3 agents run on a single node with one LLM server.

**Resources:**
- VRAM: 6GB minimum
- RAM: 20GB recommended
- Model: qwen2.5-7b-instruct-q4_K_M.gguf (4.4GB)

**Deploy:**
```bash
kubectl apply -k k8s/base/
```

### Distributed (Production)

For the hello-world capability, a single node is sufficient. The distributed overlay is provided for consistency with other capabilities.

**Deploy:**
```bash
kubectl apply -k k8s/overlays/distributed/
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PIPELINE_MODE` | `general_chatbot` | Pipeline mode |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LLAMASERVER_HOST` | `http://llama-server:8080` | LLM server URL |

### Pipeline Configuration

The hello-world capability uses a 3-agent pipeline:
- **understand**: Analyze user intent
- **think**: Execute tools if needed
- **respond**: Generate response

Set in deployment:
```yaml
env:
  - name: PIPELINE_MODE
    value: "general_chatbot"
```

---

## Resource Requirements

### LLM Server

The llama-server requires GPU resources:

```yaml
resources:
  requests:
    nvidia.com/gpu: "1"
  limits:
    nvidia.com/gpu: "1"
```

Ensure nodes have:
- NVIDIA GPU with sufficient VRAM
- nvidia-device-plugin-daemonset installed
- Node labels for GPU scheduling

---

## Prerequisites

1. **Kubernetes cluster** with GPU support
2. **Persistent volumes** for:
   - `llama-models-pvc`: LLM model storage
   - `postgres-data`: Database storage
3. **Secrets** for database credentials:
   ```bash
   kubectl create secret generic jeeves-secrets \
     --from-literal=postgres_user=assistant \
     --from-literal=postgres_password=<password>
   ```

---

## See Also

- [Capability CONSTITUTION](../jeeves_capability_hello_world/CONSTITUTION.md)
- [Docker Compose](../docker/docker-compose.yml) for local development

---

*Last Updated: 2025-01-27*
