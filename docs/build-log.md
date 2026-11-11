# Build log

What was run to build this collection, what failed and how each failure was
fixed, with the real output. Newest phase last. The build machine is one
Ubuntu 24.04.5 amd64 host (24 CPUs, 92 GiB, KVM, Docker 29.9.2 on the classic
overlay2 store, one RTX 4080 SUPER) that also runs the NVKE VMs.

## Phase 1: read and compare (2026-11-10)

- NVKR `v0.1.0` is a lightweight tag on `5163d525c52869bb8a92e83e2ef316364e5f8d2d`
  (published 2026-10-22, no release assets: the CLI is built from source).
  `.go-version` is `1.27.3`.
- Every NVKE catalog in NVKR v0.1.0 (`nvke/release`, `nvke/module-tags`,
  `node-images/*`) pins NVKE `v0.22.0` at `400c24fb6465b042be883d6b62472528520d6291`,
  tree `f3afc02f5c92f4aacda3a1655836a91bef093bfe`. omerfsen.nvke pins the same
  commit (`nvke_commit`, `node_image_nvke_commit`). Both build Ubuntu 26.04.1.
  **No difference to report.**
- NVKE `v0.23.1` (2026-11-03) is the latest stable NVKE. No NVKR release
  builds it: NVKR `main` pins `v0.23.0` and needed new DOCA OVS producers to do
  so (NVKR PR #308), so v0.1.0 cannot be repinned to it. Decision: stay on
  NVKR v0.1.0 with NVKE v0.22.0.
- Local Runs are unsigned (`unqualified-local-execution`). `nvkr release verify`
  accepts only `--lane pipeline-attested`:

  ```text
  nvkr: [NVKR-E-TRUST-POLICY-MISSING] verification policy lane "unqualified-local-execution" is unsupported
  ```

  So the verify step here checks integrity and binding (digests), not
  signatures. NVKR also does not publish disks from a local Run
  (`docs/adr/reconciliation.md`: "Ordinary local disk publication remains closed").

## Phase 2: CLI and the quickstart

### GPU passthrough set for the next boot

```shell
# omerfsen.nvke, inventory local.yml: nvke_kvm_gpu_passthrough_mode: permanent
ansible-playbook -i inventory/kvm playbooks/gpu_passthrough.yml
```

`changed=4`, then the playbook's own gate: `0000:01:00.1 is on snd_hda_intel,
not vfio-pci. On a first run this is expected: reboot the host`. The initrd
carries `/etc/modprobe.d/vfio.conf` with `vfio-pci ids=10de:2702,10de:22bb`.

### First runs of playbooks/quickstart.yml, and the fixes

| Failure | Cause | Fix |
|---|---|---|
| `'nvkr_user' is undefined` in nvkr_build | `include_role` keeps a role's defaults private | include `omerfsen.nvkr.nvkr` with `public: true` |
| `'dict object' has no attribute 'failure'` after a complete Run | NVKR omits `failure` from `lifecycle.json` when there is none | `failure \| default(none) is none` |
| `Unsupported parameters for (ansible.builtin.find) module: checksum_algorithm` | ansible-core 2.16's `find` has no such option | `find` the files, `stat` each with `checksum_algorithm: sha256` |
| `'nvkr_build_hello_version' is undefined` in the playbook | same as the first | `public: true` on the hello include |

### From scratch, then a rerun

`/var/lib/nvkr` removed and the registry container deleted, then:

```text
$ ansible-playbook playbooks/quickstart.yml
    msg: Hello, team! This is hello v1.0.0, built by NVKR. (127.0.0.1:5000/hello/releases@sha256:1d5ffc82c27b0c35f86892dc6a6cf66e18a719d0cbe95a5a39a94173b98c05a6)
localhost : ok=73   changed=16   unreachable=0    failed=0    skipped=8    rescued=0    ignored=0
real	0m57.620s

$ ansible-playbook playbooks/quickstart.yml
localhost : ok=69   changed=0    unreachable=0    failed=0    skipped=12   rescued=0    ignored=0
real	0m9.239s
```

Two fresh builds earlier in the day published the same release digest
`1d5ffc82…`: same pinned source, same bytes on this machine.

## Phase 3: NVKE outputs

### Components (nvkectl and the seed-cluster images)

`--tags components` first ran no role tasks: tags on `include_role` do not
reach the included tasks. Fix: `apply: {tags: [...]}` on each include.

```text
$ ansible-playbook playbooks/nvke_release.yml --tags components
    - 'components release: 127.0.0.1:5000/nvke/releases@sha256:ea027f5f55b05328cc34af02da44c121f85fc4eed7f3ae90b883ea1299c0089d'
localhost : ok=81   changed=8    unreachable=0    failed=0    skipped=17   rescued=0    ignored=0
real	2m13.844s
```

The pulled nvkectl:

```text
nvkectl v0.22.0 (commit: 400c24fb6465b042be883d6b62472528520d6291, built: 2026-10-21T02:06:38Z)
```

### Node image: two upstream problems

1. NVKR's local route (`scripts/nvke-os-local.sh`) failed at once in the Packer
   toolchain build:

   ```text
   ERROR: failed to build: Docker exporter is not supported for the docker driver.
   Switch to a different driver, or turn on the containerd image store, and try again.
   ```

   `toolchains/nvkr-packer/build.sh` exports with
   `--output type=docker,dest=-,rewrite-timestamp=true`, which Docker's default
   `docker` Buildx driver refuses on a daemon without the containerd image
   store, even without `rewrite-timestamp`. NVKR fixed this for its CI only
   (PR #244, already in v0.1.0); the local scripts still use whatever builder
   is current. Switching the daemon to the containerd store would hide every
   image other labs on the machine use, so the `nvkr` role creates a
   `docker-container` builder on a digest-pinned BuildKit
   (`moby/buildkit:v0.34.0@sha256:b059f8d7…`) and NVKR's commands get it through
   `BUILDX_BUILDER`. The upstream fix is prepared as a PR (see below).

2. With the builder, the toolchain built (about 12 minutes) and the Run then
   stopped at NVKR's VM admission:

   ```text
   nvkr: [NVKR-E-ENGINE-CAPABILITY] reading cgroup CPU quota at /sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/app.slice/tmux-spawn-….scope: open …/cpu.max: no such file or directory
   ```

   NVKR reads `cpu.max` in every cgroup from the process up to the root. Under
   a systemd user manager's `app.slice` (tmux, desktop terminals) the cpu
   controller is off, so the file is missing. NVKR `main` fixed this after
   v0.1.0 (PR #237, merged 2026-10-27, not in v0.1.0). Fix here: every Run starts as
   `systemd-run --scope -p CPUAccounting=yes -- runuser -u <user> -- …`, which
   puts it in its own system scope with the user's real groups (docker, kvm):

   ```text
   uid=1000(…) groups=…,988(docker),994(kvm)
   /system.slice/run-rbe39e9e….scope
   max 100000
   ```

A first try of the scope through Ansible split the command in two (a folded
YAML line that kept its newline), so attempt `nvke-os-amd64-920d6446f814-01`
failed outside the scope. NVKR attempts are immutable: it stays as a record,
and `nvkr_build_attempt_suffixes: {nvke-os-amd64: "02"}` started a new one.

```text
$ ansible-playbook playbooks/nvke_release.yml --tags node_image
    - 'node image: /var/lib/nvkr/src/nvkr-v0.1.0/.nvkr/runs/nvke-os-amd64-920d6446f814-02/outputs/nvke-node-image-amd64.qcow2'
localhost : ok=40   changed=1    unreachable=0    failed=0    skipped=9    rescued=0    ignored=0
real	13m40.055s
```

The Run record: `status: complete`, lane `unqualified-local-execution`, one
`disk-image` output, qcow2, `encryption: none`, 3,545,366,528 bytes,
`sha256:9e8c747936936634ea286d6e6fe2bfe66c10b3cc8e3c4cd5dd672072312de7f3`,
built from 11 components (agent, Calico, OVN, kubeadm distro, SPIRE agent,
installer ISOs, image inputs). The Packer toolchain the attempt used was
`sha256:b541fd371a16a74e5b96470ac648ad2ca5d24f0febf425e5362bf86d96331b22`; NVKR
keeps no stable pin for it (rebuilds did not reproduce IDs upstream), so this
is the observed ID, frozen in the attempt's inputs. The 13 minutes include a
cached toolchain build from the earlier attempt.

### Handoff

The first run failed at the node image copy: `copy`'s `checksum` option is
SHA-1, not SHA-256. Fix: copy to a temporary name, check SHA-256 against the
Run's digest, rename.

```text
$ ansible-playbook playbooks/handoff.yml
localhost : ok=121  changed=2    unreachable=0    failed=0    skipped=24   rescued=0    ignored=0
$ ansible-playbook playbooks/handoff.yml
localhost : ok=120  changed=0    unreachable=0    failed=0    skipped=25   rescued=0    ignored=0
```

It wrote `/var/lib/nvkr/handoff/nvke-vars.yml`:

```yaml
node_image_file: /var/lib/libvirt/images/nvke-node-image-amd64-nvkr-9e8c74793693.qcow2
nvke_nvkectl_file: /var/lib/nvkr/verified/ea027f5f55b05328/nvkectl/nvkectl
nvke_controller_image_archive: /var/lib/nvkr/handoff/images/nke-controller-f1d658b5301f.oci.tar
nvke_controller_image: nvkr.local/nvke/nke-controller:nvkr-f1d658b5301f
nvke_provisioned_image_archive: /var/lib/nvkr/handoff/images/cluster-api-provider-provisioned-f34d941093e8.oci.tar
nvke_provisioned_image: nvkr.local/nvke/cluster-api-provider-provisioned:nvkr-f34d941093e8
```

## Phase 4: NVKE on KVM from the NVKR outputs

After the reboot both GPU functions were on `vfio-pci` and omerfsen.nvke's
`gpu_passthrough.yml` passed (`changed=0`). omerfsen.nvke (with its
prebuilt-artifact patch) then used the handoff:

```text
TASK [omerfsen.nvke.node_image : Use the prebuilt image] ... ok
TASK [omerfsen.nvke.nvke : Install the prebuilt nvkectl] ... changed: [nvke-bootstrap]
TASK [omerfsen.nvke.nvke : Load the prebuilt seed-cluster images] ... changed: [nvke-bootstrap] => (item=/var/lib/nvkr/handoff/images/nke-controller-f1d658b5301f.oci.tar)
TASK [omerfsen.nvke.nvke : The prebuilt images loaded under their references] ... ok: [nvke-bootstrap]
```

containerd named both images from the index annotation, as NVKR's demo
expects. All four VMs started, `nvke-cp-03` with the GPU. Then every node
failed at cloud-init:

```text
status: error
errors:
	- ('scripts_user', RuntimeError('Runparts: 1 failures (runcmd) in 1 attempted commands'))
E: Unable to locate package nvke-cni-ovn-images-2.4.2
E: Unable to locate package nvke-cni-ovn-charts-2.4.2
```

The NVKR image's local repository (`/usr/lib/nvke/debs`) has
`nvke-cni-ovn-images-1.4.0`, `nvke-cni-ovn-charts-1.4.0`, Calico 3.30.1 and
kubeadm distributions 1.34.2, 1.35.3 and 1.36.3. Both of NVKR v0.1.0's node-image
catalogs (`diagnostic`, `release`) pin upstream `ovn-kubernetes/ovn-kubernetes`
v1.4.0 (`d6a3812d`); NVIDIA's OVN 2.4.2 exists only as candidate overlays bound
to the ARM64 nightly catalogs (`variants/nvidia-kvm.json`, `native-nvidia.json`),
which `scripts/nvke-os-local.sh` does not accept. Decision (Omer): run upstream
OVN-Kubernetes 1.4.0, the combination NVKR's own NVKE demo runs as its upstream
alternative. The handoff now reads the version from the catalog lock and writes
`nvke_cni_version: 1.4.0` into the vars file.

The recreated nodes found the 1.4.0 packages, then failed in the images
package's install script:

```text
nvke-cni-ovn-images-1.4.0: ctr images import failed (exit 1)
ctr: failed to extract layer (application/vnd.oci.image.layer.v1.tar+gzip sha256:09923199…) …: content digest sha256:09923199…: not found
```

The bundle's own checksum sidecar passed, so the archive was what had been
built. Inside it, one blob did not hash to its name: `09923199…`, 41,572,999
bytes, the first layer of `ovn-kube-ubuntu`, which is the upstream Ubuntu base
layer. It was already wrong in the producer's output
(`nvke-node-image-amd64/out/ovn-kube-ubuntu/ovn-kube-ubuntu.oci.tar`, built by
NVKR's own pinned rootless BuildKit) and is invalid gzip
(`invalid compressed data--crc error`). Against the pristine layer from Docker
Hub exactly three bytes differ, four bytes apart, each by one flip of the same
bit:

```text
offset 1363382: 377 -> 337 (xor 32)
offset 1363386: 234 -> 274 (xor 32)
offset 1363390: 246 -> 206 (xor 32)
```

That is the pattern of a memory fault, not of software. The build machine has
non-ECC DDR5 (2 × 48 GB) running at its 6400 MT/s XMP profile (JEDEC 4800), and
non-ECC memory logs nothing. Not an NVKR bug; NVKR does not re-check the
layers of images it bakes into a disk, so the flip surfaced only at first boot.
Fix here: `node_image` now checks that every blob of every OCI image the Run
produced hashes to its name, which fails the play on attempt 02:

```text
stdout: 'corrupt blob: 09923199ca0ebd3ad9fb1dd1d0ab85d2b86aa388b988c8d4c8ee4f660fdb9e9e'
```

Attempt 03 then failed before building: the Buildx builder, created while the
GPU was still on the host driver, had been given the GPU by Buildx
(`DeviceRequests: [{"Capabilities":[["gpu"]],"Count":-1}]`), and with the GPU on
vfio-pci its container no longer starts:

```text
nvidia-container-cli: initialization error: nvml error: driver not loaded
```

A builder created with the GPU on vfio-pci gets no device request. The `nvkr`
role now boots the builder on each run and recreates one that does not start.
The node image was rebuilt as attempt 04.

With a clean image the nodes passed cloud-init, and `nvkectl bootstrap site`
side-loaded the NVKR images and deployed the controller from them:

```text
msg="loading image into bootstrap kind cluster" ... image=nvkr.local/nvke/cluster-api-provider-provisioned:…
msg="deploying the controller onto bootstrap kind cluster" ... image=nvkr.local/nvke/nke-controller:nvkr-f1d658b…
```

Provisioning then stopped at the CNI:

```text
failed to install CNI on node nvke-mgmt-cp-1969e46a: rpc error: code = FailedPrecondition desc = CNI charts Debian package must be installed before InstallCNI ("nvke-cni-ovn-charts-2.4.2")
```

The site spec had `cniVersion: ""`, so the controller used its default, 2.4.2.
omerfsen.nvke used `nvke_cni_version` only for the node packages, never in the
site spec; with its default (2.4.2) the two always agreed. The patch now passes
`cluster.cniVersion=<nvke_cni_version>` to `nvkectl generate sitespec`, as NVKR's
own demo does for its upstream OVN selection.

With the site spec fixed and node image attempt 04 (clean), the cluster came up:

```text
$ ansible-playbook -i inventory/kvm playbooks/kvm.yml -e @/var/lib/nvkr/handoff/nvke-vars.yml
nvke-bootstrap : ok=92   changed=30   failed=0
nvke-cp-01..03 : ok=20   changed=2    failed=0
real	8m41.639s

$ kubectl get nodes -o wide
nvke-mgmt-cp-0217e043   Ready   control-plane   v1.36.3   192.168.90.103   Ubuntu 26.04.1 LTS   7.0.0-1025-nvidia (amd64)   containerd://2.3.0
nvke-mgmt-cp-717e6a77   Ready   control-plane   v1.36.3   192.168.90.101   Ubuntu 26.04.1 LTS   7.0.0-1025-nvidia (amd64)   containerd://2.3.0
nvke-mgmt-cp-9c83cbc0   Ready   control-plane   v1.36.3   192.168.90.102   Ubuntu 26.04.1 LTS   7.0.0-1025-nvidia (amd64)   containerd://2.3.0
```

The OVN image on a node is the manifest NVKR built
(`sha256:425ad9c6296e0742183cb0128f9cd9168478d5b3f920cb162279b785530df2b1` on both
sides); the bootstrap VM's nvkectl hashes to the verified one (`4a5ea3f8…`) and its
seed images are `nvkr.local/nvke/*:nvkr-<digest>`.

omerfsen.aicr 0.2.0 on top: `failed=0` in 8m48s, 71 pods Running, the GPU node
labelled `NVIDIA-GeForce-RTX-4080-SUPER`, AICR validation 3/3 passed. The DCGM
image's first pull failed and `dcgm-exporter` restarted until DCGM was up; both
recovered on their own. omerfsen.nvke's GPU jobs: nvidia-smi, CUDA vector add,
TensorFlow, PyTorch, TensorRT and DCGM metrics, 6 of 6 PASS. Reruns: handoff,
nvke and aicr all `changed=0`.

The NICo lab VMs on the machine were destroyed at Omer's request to free about
36 GB (omerfsen.nico's `kvm_destroy.yml`, plus a leftover `nico-server-03`
defined by test-only variables).

## Upstream: Buildx docker-driver preflight

Reproduced on its own with a two-line Dockerfile: the default `docker` driver
fails `--output type=docker,dest=-` with and without `rewrite-timestamp`; a
`docker-container` builder exports the archive. No open issue or PR covers
local runs (PR #244 changed only `.github/workflows/nvkr-native-toolchains.yml`).

The prepared change to `toolchains/nvkr-packer/build.sh` reads the active
builder's driver (`docker buildx inspect`, which honors `BUILDX_BUILDER`) and
the daemon's storage (`docker info`), and refuses the `docker` driver on the
classic store before building, with the remedy. A new test covers refusal and
both admitted cases, and fails without the change. On the build machine the
default builder is now refused in 0.14 s with the remedy instead of buildx's
bare error; the container builder goes straight into the build. With Go 1.27.3:
the packer package tests pass, `make lint` (golangci-lint 2.15.0) reports 0 issues,
and every other `make check` target passes except four packages (`internal/nvkedemo`,
`internal/qemutpm`, `pkg/nvkr/catalogmaintenance`, `pkg/nvkr/factory`) that
fail the same way on unmodified `main` on this machine.

## Decisions

- Go: NVKR pins 1.27.3 and its Makefile refuses other versions. The system Go
  is 1.27.4; the collection installs 1.27.3 separately (checksum verified) and
  leaves the system Go alone.

## Independent review (2026-11-10)

A separate reviewer (Claude Fable 5.2), given the code and diffs only, read this
collection, the omerfsen.nvke patch, the nvsentinel-mcp lab fix and the proposed
NVKR upstream change. No high-severity defects; every NVKR command, flag, path
and record field the roles use was confirmed against v0.1.0. Fixed here:

| Finding | Fix |
|---|---|
| Reads of NVKR's `0700` attempt and pull directories ran as the connection user, so a separate `nvkr_user` broke | Every such read runs as `nvkr_user` |
| The Buildx check looked at the daemon-wide container, not the per-user builder record | Decides from `docker buildx inspect --bootstrap` and the container image; recreates with `rm -f` first |
| Root ran `systemd-run`/`runuser`/`tail` through a `PATH` the build user owns, and wrote the log as root | Absolute paths; the log is written by the build user's shell |
| Changing `nvkr_handoff_image_prefix` reused an archive named only by digest | Archive names carry a hash of the reference |
| A half-made hello source repository was never redone | Rebuilt from a clean copy unless a completion marker exists |
| Components were fixed to amd64 while the node image follows the host | Platform defaults to `linux/<nvkr_arch>` |
| README called omerfsen.nvke 0.2.0 handoff-capable; docs overstated two checks | Wording now matches the code; lab output updated to attempt 04 |
| `build_ignore` narrower than `.gitignore` | Added `*.pem`, `.vault_pass*`, `*.img`, `*.raw`, `importer_result.json` |

Retested after the fixes: a new hello attempt (`hello-…-02`) built and published
through the new start path, its log owned by the build user; quickstart,
`nvke_release` and handoff each rerun `changed=0`; `ansible-lint` production clean.
