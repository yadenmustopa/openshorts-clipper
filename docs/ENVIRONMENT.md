# Execution Environment — Verified

This document exists because Phase 0/1 work needs to state, with evidence
rather than assumption, exactly what machine this agent has been running
commands on. It was written in direct response to a correction from the
user: do not assume "no GPU detected" means the target PC is CPU-only, and
do not assume this agent's terminal is a disposable cloud sandbox — check.

## Verdict

**This agent has been executing directly on the user's real local machine
(bare metal), not a cloud VM and not a container.** It is the same machine
referred to throughout Phase 0/1 as "this environment." There is no
separate "target PC" to still gain access to — this is it.

## Evidence

| Check | Command | Result |
|---|---|---|
| Virtualization | `systemd-detect-virt` | `none` (bare metal) |
| Container marker | `/.dockerenv` | absent |
| Cgroup | `/proc/1/cgroup` | `0::/init.scope` (not a container-scoped cgroup) |
| OS | `/etc/os-release` | `Pop!_OS 22.04 LTS` (`ID=pop`, `ID_LIKE="ubuntu debian"`), kernel `6.8.0-85-generic` |
| Hostname | `hostnamectl` | `pop-os`, chassis `desktop` |
| Hardware vendor/model | `hostnamectl` | Micro-Star International Co., Ltd. (MSI), model `MS-7C52` |
| CPU | `lscpu` | AMD Ryzen 5 5600G with Radeon Graphics, 12 logical cores |
| RAM | `free -h` | 54 GiB total |
| GPU (PCI) | `lspci \| grep -i vga` | `Advanced Micro Devices, Inc. [AMD/ATI] Cezanne (rev c9)` — the Ryzen 5600G's **integrated AMD Radeon graphics** |
| NVIDIA packages | `dpkg -l \| grep nvidia` | none installed |
| `nvidia-smi` | — | not present (consistent with no NVIDIA GPU, not a false negative from a container hiding it) |

## What this means for the pipeline, precisely

The earlier Phase 0 framing ("no GPU detected → CPU-only") was imprecise and
is corrected here: there **is** a GPU in this machine (the Ryzen 5600G's
integrated AMD Radeon graphics), but OpenShorts' GPU-accelerated paths —
`osrender/`'s CUDA kernels, NVENC hardware encoding, CUDA-accelerated
torch/ultralytics/mediapipe — are explicitly **NVIDIA-only** per upstream's
own README ("GPU acceleration (optional, NVIDIA)") and Dockerfile
(`nvidia-smi`, NVIDIA Container Toolkit, `--gpus all`). An AMD iGPU does not
satisfy that path. So:

- **Correct statement:** this machine has no CUDA-capable GPU, so
  OpenShorts' GPU acceleration path is unavailable and the CPU path
  (`requirements-cpu.lock`, ffmpeg software encode, CPU torch build) is the
  only one applicable here — this was the right install path, for the right
  reason, just stated too loosely before.
- **Incorrect statement (now retracted):** "the PC is CPU-only" as a
  general hardware claim — it has a GPU, just not an NVIDIA one.
- No further environment classification is needed before continuing Phase 1
  on this machine: it is not a stand-in for the user's PC, it is the user's
  PC.

## Installed and available on this machine (confirmed, not assumed)

- Docker 29.1.2, usable for the project's `docker-compose.yml` stack if a
  full-stack run is wanted later.
- ffmpeg 5.1.1-static, git 2.34.1, Python 3.11.4 (`/home/denevill/anaconda3`),
  Node 22.23.1 / npm 10.9.8.
- **Ollama 0.31.1**, already running as a local service
  (`http://localhost:11434`), with these models already pulled:
  `qwen3:4b`, `qwen2.5-coder:1.5b`, `llava:7b` (vision-capable, llama family),
  `nomic-embed-text` (embeddings). This is exactly the kind of
  OpenAI-compatible local server `llm_backend.py` / `LLM_BASE_URL` targets —
  no installation needed for Phase 1's local-LLM validation.
- 50 GB free on the `/mnt/nvme` volume at the time of Phase 0 (disk usage
  should be rechecked before any large model-weight or Docker-image work).
