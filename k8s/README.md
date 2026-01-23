# Kubernetes Deployment Manifests

**Parent:** [README.md](../README.md)

---

## Overview

This directory contains Kubernetes manifests for deploying the Jeeves Code Analysis capability. The manifests are organized using Kustomize for easy customization across environments.

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
        ├── node1-deployment.yaml  # perception, intent, integration
        ├── node2-deployment.yaml  # traverser (code-specialized)
        └── node3-deployment.yaml  # planner, synthesizer, critic
```

---

## Deployment Modes

### Single-Node (Development)

All 7 agents run on a single node with one LLM server.

**Resources:**
- VRAM: 6GB minimum
- RAM: 20GB recommended
- Model: qwen2.5-7b-instruct-q4_K_M.gguf (4.4GB)

**Deploy:**
```bash
kubectl apply -k k8s/base/
```

### Distributed (Production)

Agents distributed across 3 nodes with specialized models:

| Node | Agents | Model | VRAM | Purpose |
|------|--------|-------|------|---------|
| node1 | perception, intent, integration | qwen2.5-7b | 6GB | Fast agents |
| node2 | traverser | deepseek-coder-6.7b | 6GB | Code-specialized |
| node3 | planner, synthesizer, critic | qwen2.5-14b | 12GB | Reasoning hub |

**Deploy:**
```bash
kubectl apply -k k8s/overlays/distributed/
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PIPELINE_MODE` | `full` | Pipeline mode: `standard` (fast) or `full` (thorough) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LLAMASERVER_HOST` | `http://llama-server:8080` | LLM server URL |

### Pipeline Modes

Controlled via `PIPELINE_MODE` environment variable:

- **`full`** (default): 7 agents including critic validation
- **`standard`**: 6 agents, skips critic for faster responses

Set in deployment:
```yaml
env:
  - name: PIPELINE_MODE
    value: "full"
```

Or via ConfigMap:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: jeeves-config
data:
  pipeline_mode: "full"
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

### Node Selectors

For distributed deployment, label nodes appropriately:

```bash
# Standard GPU nodes (6GB VRAM)
kubectl label node <node-name> jeeves.io/node-type=standard

# High-memory GPU nodes (12GB+ VRAM)
kubectl label node <node-name> jeeves.io/node-type=high-memory
```

---

## Prerequisites

1. **Kubernetes cluster** with GPU support
2. **Persistent volumes** for:
   - `llama-models-pvc`: LLM model storage
   - `workspace-pvc`: Repository to analyze (read-only)
   - `postgres-data`: Database storage
3. **Secrets** for database credentials:
   ```bash
   kubectl create secret generic jeeves-secrets \
     --from-literal=postgres_user=assistant \
     --from-literal=postgres_password=<password>
   ```

---

## Derived From

These manifests were extracted from `config/deployment.py` PROFILES to follow infrastructure-as-code principles. The Python module now only contains `CODE_ANALYSIS_AGENTS` list.

See also:
- [Capability CONSTITUTION](../jeeves-capability-code-analyser/CONSTITUTION.md)
- [Docker Compose](../docker/docker-compose.yml) for local development

---

*Last Updated: 2026-01-23*
