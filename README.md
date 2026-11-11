# omerfsen.nvkr

An Ansible collection and lab that builds NVIDIA Kubernetes Engine (NVKE)
artifacts with [NVIDIA Kubernetes Recipes (NVKR)](https://github.com/dsx-ai-factory/nvkr)
on one Linux host, checks them, and hands them to
[omerfsen.nvke](https://github.com/omerfsen/nvke) so its KVM management cluster
boots from exactly what NVKR built.

NVKR turns pinned source into NVKE's CLI, container images and node OS images
and records which inputs produced each one. It does not install anything. This
collection installs the `nvkr` CLI from a pinned release, runs it locally,
publishes what NVKR allows to a local registry, pulls it back and checks every
digest, and writes the vars omerfsen.nvke needs:

```text
pinned source ─▶ nvkr (local Runs) ─▶ local registry ─▶ checked outputs ─┐
                     └─▶ node image + Run record ────────────────────────┴─▶ omerfsen.nvke ─▶ omerfsen.aicr
```

> **Disclaimer.** This is an independent community project. It is not affiliated
> with, sponsored by or endorsed by NVIDIA. NVKR, NVKE and AICR are previews and
> are not recommended for production use. NVIDIA, NVKE and NVKR are trademarks of
> NVIDIA Corporation.

## Contents

| Name | Kind | Does |
|---|---|---|
| `omerfsen.nvkr.nvkr` | role | Prerequisites, the exact Go of the NVKR release (checksum verified), a Buildx builder, and the `nvkr` CLI built from a pinned tag |
| `omerfsen.nvkr.nvkr_build` | role | Local OCI registry; NVKR Runs for the quickstart, the NVKE components and the node image; pull-back digest checks of a release |
| `omerfsen.nvkr.nvkr_handoff` | role | Node image, nvkectl and seed-cluster images prepared for omerfsen.nvke, plus its vars file |
| `omerfsen.nvkr.quickstart` | playbook | Smoke test: NVKR's hello example built, published, pulled back, checked and run |
| `omerfsen.nvkr.nvke_release` | playbook | nvkectl, `nke-controller`, `cluster-api-provider-provisioned` and the amd64 node image |
| `omerfsen.nvkr.handoff` | playbook | The handoff to omerfsen.nvke |

## Support matrix

| | Status |
|---|---|
| Build host | Ubuntu 24.04 amd64 with Docker and KVM: tested. Debian, and Ubuntu arm64 (the roles and NVKR support them): not tested. |
| NVKR | v0.1.0 only |
| NVKE built | v0.22.0, the release NVKR v0.1.0 pins (the same omerfsen.nvke pins) |
| Node image | non-FDE QCOW2, Ubuntu 26.04.1, amd64 |
| omerfsen.nvke | Needs its prebuilt-artifact options (`node_image_file`, `nvke_nvkectl_file`, `nvke_*_image_archive`, `cluster.cniVersion` from `nvke_cni_version`), proposed on its branch `dev/osen/prebuilt-artifacts` and not in a release yet (0.2.0 lacks them). See [handoff](docs/how-it-works.md#the-handoff). |
| Ansible | ansible-core 2.16.19 |
| Tested | Ubuntu 24.04 amd64 build host with KVM, Docker 29.9 (classic store), one RTX 4080 SUPER passed through. Quickstart from scratch `failed=0`, rerun `changed=0`. NVKE outputs built and checked. omerfsen.nvke 0.2.0 with the prebuilt-artifact patch booted 3 control-plane nodes (Kubernetes 1.36.3, Ubuntu 26.04.1) from the NVKR image, nvkectl and seed images; omerfsen.aicr 0.2.0 on top: `aicr validate` 3/3, GPU jobs 6/6 (nvidia-smi, CUDA, TensorFlow, PyTorch, TensorRT, DCGM metrics). Reruns of handoff, nvke and aicr `changed=0`. |

## Component versions

### Pinned by this collection

| Component | Version | Where |
|---|---|---|
| NVKR | `v0.1.0`, commit `5163d525` (a moved tag fails the run) | `nvkr_version`, `nvkr_commit` |
| Go for NVKR | 1.27.3, SHA-256 per architecture from go.dev | `nvkr_go_version`, `nvkr_go_sha256` |
| BuildKit (Buildx builder) | `moby/buildkit:v0.34.0@sha256:b059f8d7…` | `nvkr_buildkit_image` |
| Local registry | `registry:3.1.2@sha256:38907510…` | `nvkr_build_registry_image` |
| NVKE release the handoff accepts | v0.22.0, commit `400c24fb` | `nvkr_handoff_nvke_version`, `nvkr_handoff_nvke_commit` |

### Built or acquired by NVKR from its v0.1.0 catalogs

Pinned by NVKR's catalogs and locks, not by this collection. The complete list,
with every source commit, build image, output digest and package version, is
[docs/components.md](docs/components.md), generated from the build by `make components`.

| Component | Version | NVKR catalog |
|---|---|---|
| nvkectl, `nke-controller`, `cluster-api-provider-provisioned` | NVKE v0.22.0 @ `400c24fb` | `inputs/catalogs/nvke/release` |
| nvke-agent | 0.22.0 | `inputs/catalogs/node-images/diagnostic` |
| Ubuntu installer ISO | 26.04.1 (digest-pinned) | same |
| Kubernetes packages (kubeadm distribution) | 1.36.3 (also stages 1.35.3, 1.34.2) | same |
| OVN-Kubernetes | upstream v1.4.0 @ `d6a3812d` (see known gaps) | same |
| Calico | 3.30.1 | same |
| SPIRE agent | 1.14.1 with TPM plugin 1.9.0 | same |
| Packer toolchain image | built from `toolchains/nvkr-packer` source locks (Packer 1.15.4, QEMU plugin 1.1.6); no stable pin, and two builds here gave different IDs (`b541fd37…`, `3a7805e2…`) | NVKR's local route |
| Utility containers | digest-pinned in NVKR's Environments (Alpine for hello, Go for NVKE) | `demos/quickstart`, `docs/examples/nvke-tutorial` |

## Quick start

On the build host, as a user with sudo:

```shell
git clone https://github.com/omerfsen/nvidia-nvkr.git && cd nvidia-nvkr
make dev PYTHON=python3.12
.venv/bin/ansible-playbook playbooks/quickstart.yml     # about 1 minute
.venv/bin/ansible-playbook playbooks/nvke_release.yml   # 15-30 minutes, most of it the node image
.venv/bin/ansible-playbook playbooks/handoff.yml
```

Then, in omerfsen.nvke with its prebuilt-artifact options:

```shell
ansible-playbook -i inventory/kvm playbooks/kvm.yml -e @/var/lib/nvkr/handoff/nvke-vars.yml
```

Every playbook can be rerun: completed NVKR attempts are not run again and a rerun
reports `changed=0`. The full walkthrough, with GPU passthrough and AICR, is the
[lab](docs/lab.md).

## Known upstream gaps (NVKR v0.1.0)

- **Local Runs are unsigned.** `nvkr release verify` accepts only the
  `pipeline-attested` lane, which is signed by NVKR's generated GitHub Actions
  workflow. The checks here prove the bytes are what NVKR built and recorded on
  this host (digests against the Run and the release metadata), not who built them.
- **Disks are not published from a local Run** ("ordinary local disk publication
  remains closed"). The node image stays with its Run record and the handoff checks
  it against that record.
- **The node image is not NVKE's own image.** NVKR v0.1.0's node-image catalogs
  stage upstream OVN-Kubernetes v1.4.0; NVKE v0.22.0's Packer image stages, and NVKE
  pins, NVIDIA's OVN-Kubernetes 2.4.2. NVKR has NVIDIA OVN only as candidate overlays
  for its ARM64 nightly catalogs. The cluster here runs 1.4.0, the combination NVKR's
  own NVKE demo runs as its upstream alternative; it is not on NVKE v0.22.0's
  supported list.
- **The Packer toolchain image has no stable pin**: NVKR rebuilds it from source
  locks each attempt and freezes the observed image ID.
- **NVKE v0.23.1**, the latest stable NVKE, cannot be built with NVKR v0.1.0; NVKR
  `main` builds v0.23.0 with new producers. This collection stays on v0.22.0 until an
  NVKR release pins v0.23.x.
- **Two NVKR v0.1.0 defects are worked around:**
  - The Packer toolchain export needs a container-backed Buildx builder on a classic-store Docker daemon. The `nvkr` role creates one; a fix for NVKR itself is proposed upstream.
  - VM admission fails where the cgroup cpu controller is off. Each Run starts in its own systemd scope; NVKR `main` fixed this after v0.1.0.
- **Only the seed-cluster images are used.** omerfsen.nvke bootstraps the management
  cluster; it does not install NVKE's management plane, so NVKR's chart and
  dependency-image outputs (PostgreSQL, SPIRE, Temporal, NKTP) are not built here.

## Documentation

- [How it works](docs/how-it-works.md): the flow, the Runs, what is checked and what is not, the handoff, the layout on disk.
- [Lab](docs/lab.md): the full walkthrough, ready to record.
- [Components](docs/components.md): every component version in the build, read from the Runs (`make components`).
- [Variables](docs/variables.md): every role variable, generated from the argument specs (`ansible-doc -t role omerfsen.nvkr.<role>` shows the same).
- [Troubleshooting](docs/troubleshooting.md): each failure seen while building this, and the fix.
- [Build log](docs/build-log.md): what was run, what failed and how it was fixed, with real output.

## Roadmap

- Real local signatures with `nvkr run qualify-local` (local keys; upstream has run it on ARM64 only).
- The hosted route: NVKR's generated GitHub Actions workflow with a self-hosted KVM runner, verified with `nvkr release verify --lane pipeline-attested`.
- The next NVKR release: its Environments need `toolchainAccess.publicRoots` (NVKR PRs #435, #446), single-document inputs (#443), the new version stamp (#278) and NVKE v0.23.x (#308).
- NVIDIA OVN-Kubernetes 2.4.2 on the amd64 node image, once NVKR offers it for amd64.
- AICR bundles built by NVKR (NVKR PR #239) for omerfsen.aicr.
- Test arm64 and Debian build hosts.

## License

Apache License 2.0, see [LICENSE](LICENSE). NVKR, NVKE and AICR are separate
projects under their own licenses; this collection downloads and builds them, it
does not redistribute them.
