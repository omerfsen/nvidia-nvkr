# Troubleshooting

Each entry is a failure seen while building this collection (see the
[build log](build-log.md)), what it means and what to do. Run logs are in
`/var/lib/nvkr/logs/<attempt>.log`; the role prints their last 40 lines when a
Run fails.

## `Docker exporter is not supported for the docker driver`

```text
ERROR: failed to build: Docker exporter is not supported for the docker driver.
Switch to a different driver, or turn on the containerd image store, and try again.
```

NVKR's Packer toolchain build (`toolchains/nvkr-packer/build.sh`, called by
`scripts/nvke-os-local.sh`) exports with `--output type=docker,dest=-`, which
Docker's default `docker` Buildx driver cannot do on a daemon using the classic
image store. The `nvkr` role creates a `docker-container` builder
(`nvkr_buildx_builder`) and every Run gets it through `BUILDX_BUILDER`. If you run
NVKR's scripts by hand, do the same:

```shell
docker buildx create --name nvkr-buildkit --driver docker-container --bootstrap
export BUILDX_BUILDER=nvkr-buildkit
```

Enabling the containerd image store also works, but it hides the images the
daemon already holds.

## `NVKR-E-ENGINE-CAPABILITY ... reading cgroup CPU quota ... cpu.max: no such file or directory`

NVKR v0.1.0's admission for VM builds reads `cpu.max` in every cgroup from the
process up to the root, and the file is missing where the cpu controller is off,
as in a systemd user manager's `app.slice` (tmux, desktop terminals). The role
starts each Run in its own systemd scope with CPU accounting
(`nvkr_build_run_scope: true`, the default). By hand:

```shell
sudo systemd-run --scope -p CPUAccounting=yes -- runuser -u "$USER" -- bash scripts/nvke-os-local.sh <attempt> 4
```

`runuser` matters: `systemd-run --uid` keeps root's supplementary groups and loses
`docker` and `kvm`. NVKR `main` accepts a disabled controller (PR #237).

## `Attempt ... was started before and did not complete`

NVKR attempts are immutable: a failed or interrupted attempt stays as a record and
its name cannot be reused. The role refuses rather than hide it. Read its log, fix
the cause, then start a new attempt for that Run only:

```yaml
# inventory/lab/group_vars/all/local.yml
nvkr_build_attempt_suffixes:
  nvke-os-amd64: "02"     # or hello, nvke-components
```

`nvkr_build_attempt_suffix` changes it for every Run (and rebuilds them all).

## `verification policy lane "unqualified-local-execution" is unsupported`

```text
nvkr: [NVKR-E-TRUST-POLICY-MISSING] verification policy lane "unqualified-local-execution" is unsupported
```

Expected. `nvkr release verify` only accepts `--lane pipeline-attested`: releases
signed by NVKR's generated GitHub Actions workflow. Local Runs are unsigned; the
`verify` entry point checks digests instead (see [how it works](how-it-works.md)).

## `Go go1.27.4 does not match pinned go1.27.3`

NVKR's Makefile refuses any Go but the one in `.go-version`. The `nvkr` role installs
that Go under `/var/lib/nvkr/go-<version>` and puts it first on `PATH` for NVKR's
commands, so the system Go can be newer. If you build by hand:

```shell
PATH=/var/lib/nvkr/go-1.27.3/bin:$PATH GOTOOLCHAIN=local make build
```

## `release pull`: destination exists

`release pull --out` refuses an existing directory. The role pulls into
`<output>.partial` and renames it when complete, so an interrupted pull is retried
on the next run. A directory without `.partial` was completed and checked.

## The Buildx builder does not start: `nvml error: driver not loaded`

```text
#1 [internal] booting buildkit
nvidia-container-cli: initialization error: nvml error: driver not loaded
```

Buildx gives a `docker-container` builder the host's GPUs when it creates the
builder. After the GPU is passed through to a VM (vfio-pci) the container cannot
start. The `nvkr` role boots the builder on every run and recreates one that does
not start; by hand: `docker buildx rm nvkr-buildkit` and create it again. A Run
that failed here keeps its reserved attempt: start a new one with
`nvkr_build_attempt_suffixes`.

## The registry port is taken

The registry listens on `127.0.0.1:5000`. Set `nvkr_build_registry_port` to a free
port; the role replaces the container (its data stays) and the Environments publish
to the new address. Releases published at the old address keep its reference: pull
them from the new port only after re-running the build, which gives new attempts.

## The node image build needs room

NVKR's admission checks 8 CPUs, 10 GiB of memory and 64 GiB of free workspace before
starting QEMU; allow about 90 GiB on the filesystem holding `/var/lib/nvkr` before a
bake. KVM must be usable by the build user (`exec 3<>/dev/kvm`; the role adds it to
the `kvm` group).

## A node's first boot fails: `ctr images import failed` / `content digest ... not found`

A layer in an OCI image baked into the node image does not hash to its digest.
The `node_image` step now refuses such a Run (`corrupt blob: <digest>`). On the
build machine this was three single-bit flips in one layer: a memory fault
(non-ECC DDR5 at its XMP profile). Check the memory (memtest86+, or the RAM at
JEDEC speed), then start a new attempt with `nvkr_build_attempt_suffixes`.

## omerfsen.nvke: the GPU node does not start

`nvke-cp-03` takes the GPU with `managed='no'`, so it starts only when `vfio-pci`
owns the card. After switching omerfsen.nvke's `nvke_kvm_gpu_passthrough_mode` to
`permanent` and running its `gpu_passthrough.yml`, reboot and check:

```shell
lspci -nnk -s 01:00   # Kernel driver in use: vfio-pci, for both functions
```
