# AGENTS.md

Guidance for coding agents and people working in this repo. `CLAUDE.md` imports this file, so
this is the only copy. [README.md](README.md) covers using the collection.

## What this repo is

`omerfsen.nvkr`, an Ansible collection and lab: it installs the
[NVIDIA Kubernetes Recipes](https://github.com/dsx-ai-factory/nvkr) (NVKR) CLI from a pinned
release, runs NVKR locally to build NVKE artifacts (nvkectl, the two seed-cluster images, the node
OS image), checks them, and hands them to [omerfsen.nvke](https://github.com/omerfsen/nvke), which
deploys a KVM management cluster from exactly those artifacts.
[omerfsen.aicr](https://github.com/omerfsen/aicr) then adds the GPU runtime.

It does **not** install or deploy NVKE itself; that is omerfsen.nvke. Keep NVKE, AICR and NICo
logic in their own collections.

## How it works

```text
nvkr role ── nvkr CLI ──▶ nvkr_build ── run local --publish ──▶ local registry ──▶ verify (digests)
                              └── scripts/nvke-os-local.sh ──▶ node qcow2 + Run record ──┐
                                                                     nvkr_handoff ◀──────┘
                                                                          └── nvke-vars.yml ──▶ omerfsen.nvke
```

| Path | What it holds |
|---|---|
| `roles/nvkr/` | Go (exact version, checksum), Docker check, Buildx builder, NVKR checkout and `make build` |
| `roles/nvkr_build/` | Registry, Runs (`hello`, `components`, `node_image`), `verify`; `tasks/run.yml` is the one place a Run starts |
| `roles/nvkr_handoff/` | Seed-image archives, node image copy, `nvke-vars.yml` |
| `playbooks/` | `quickstart.yml`, `nvke_release.yml`, `handoff.yml` |
| `inventory/lab/` | The build host; machine overrides in the gitignored `group_vars/all/local.yml` |
| `tools/gen-variables-doc.py` | **Generates** `docs/variables.md` from the argument specs (`make docs`) |
| `tools/gen-components-doc.py` | **Generates** `docs/components.md` from the build on this host (`make components`) |
| `docs/build-log.md` | Every step, failure and fix, with real output |
| `docs/lab.md` | The walkthrough, written to be recorded |

## Commands

```shell
make dev PYTHON=python3.12   # venv, dependencies, this repo linked as omerfsen.nvkr
make lint                    # ansible-lint --profile production and playbook syntax
make docs                    # docs/variables.md from the argument specs
make components              # docs/components.md from this host's newest completed Runs
make quickstart              # NVKR's hello example: build, publish, pull back, check, run
make release                 # nvkectl, seed images (published + checked) and the node image
make handoff                 # nvke-vars.yml for omerfsen.nvke
```

Runs need a Debian/Ubuntu host with Docker, KVM, sudo and about 90 GiB free. Logs:
`/var/lib/nvkr/logs/<attempt>.log`.

## Rules

- **Never guess an NVKR command, flag, schema field or path.** Take it from the NVKR source or docs
  at the pinned tag (`/var/lib/nvkr/src/nvkr-v0.1.0`, or `bin/nvkr <cmd> --help`). If it is not
  documented, say so and stop.
- **Pins:** NVKR by tag plus commit (a moved tag fails the run); Go by version plus SHA-256; images by
  digest. Never `main`, never a floating tag.
- **NVKR attempts are immutable.** Never delete or reuse one to make a run pass; start a new one
  with `nvkr_build_attempt_suffixes`. Keep failed attempts as records.
- **Do not edit the NVKR checkout or its catalogs.** Definitions and Environments this collection
  writes go under `<checkout>/.nvkr/omerfsen/`, which NVKR's `.gitignore` covers.
- **Say what is and is not checked.** Local Runs are unsigned; `verify` checks digests, not
  signatures. Keep the README's known-gaps list true.
- **Idempotent:** a second run reports `changed=0`. Prove it after any role change.
- **Tested means run on a real host.** Paste the actual output into `docs/build-log.md`; never mark
  something done from a syntax check.
- Every role variable is in its `meta/argument_specs.yml`; run `make docs` after changing one.
  `make lint` must pass with the production profile.
- In anything published (docs, commits, PRs), say "the build machine", never a host name or a
  LAN address outside the lab's libvirt network.

## Commits, PRs and releases

- Conventional Commits, `<type>(<scope>): <summary>`, scope the role or area
  (`feat(nvkr_build): ...`, `docs(lab): ...`). One line; a body only for several unrelated parts.
- The pipelines are vendored from [omerfsen/cicd](https://github.com/omerfsen/cicd)
  (`.github/cicd/config`, `.github/cicd/SOURCE`); update them with its `install.sh`, never by hand.
- release-please opens the release PR and tags `vX.Y.Z`; the tag publishes to Galaxy. A version
  can never be re-uploaded to Galaxy.
- Do not push, tag or publish without the owner's go-ahead.
