# Components

Every component version that went into the NVKR build on the build machine,
read from the build itself by `make components` (`tools/gen-components-doc.py`):
the NVKR CLI, the Plans and records of the newest completed Runs, their
packages and logs, and this collection's role defaults. Regenerate it after
an NVKR bump or a new build.

## NVKR and this collection's pins

| Component | Version | Pinned in |
|---|---|---|
| NVKR CLI | `nvkr version v0.1.0 (5163d525)` | `nvkr_version`, `nvkr_commit` (`5163d525c52869bb8a92e83e2ef316364e5f8d2d`) |
| Go for the CLI | 1.27.3 (NVKR's `.go-version`) | `nvkr_go_version`, `nvkr_go_sha256` |
| BuildKit for the Packer toolchain build | `moby/buildkit:v0.34.0@sha256:b059f8d7226d` | `nvkr_buildkit_image` |
| Local registry | `registry:3.1.2@sha256:38907510915c` | `nvkr_build_registry_image` |

## Run `hello-6206ccd1d81b-01`

Lane `unqualified-local-execution`, Plan `sha256:77440f8df5013001`.

### Outputs

| Output | Kind | Digest |
|---|---|---|
| `hello` | executable | `sha256:d66a8d172fa55a36863680d98041702d9c736ef909c9f813be4adbb1520c7548` |

### Components built or acquired

| Component | Source | Version | Commit | Built with |
|---|---|---|---|---|
| `hello` | https://demo.example.invalid/hello | v1.0.0 | `bf37741d234a` | oci-hermetic `alpine@sha256:294b683cb724` |

## Run `nvke-components-0aa9434b6b65-01`

Lane `unqualified-local-execution`, Plan `sha256:df6b61a7db4a7030`.

### Outputs

| Output | Kind | Digest |
|---|---|---|
| `cluster-api-provider-provisioned` | oci | `sha256:f34d941093e85423d8a4049adf1a01500711906a6c3437236902a14f9185b30a` |
| `nvke-controller` | oci | `sha256:f1d658b5301f6f49980cef55b81c84969f6d01b7c79a317efd0e9b7b470ec058` |
| `nvkectl` | executable | `sha256:5b1005dd0612fd76408d3bd5a918912ac973abf93ac07aa19a6ae258d931541f` |

### Components built or acquired

| Component | Source | Version | Commit | Built with |
|---|---|---|---|---|
| `cluster-api-provider-provisioned` | dsx-ai-factory/nvke | v0.22.0 | `400c24fb6465` | buildkit-rootless `moby/buildkit@sha256:f8a833b2de9d` |
| `nvke-controller` | dsx-ai-factory/nvke | v0.22.0 | `400c24fb6465` | buildkit-rootless `moby/buildkit@sha256:f8a833b2de9d` |
| `nvkectl` | dsx-ai-factory/nvke | v0.22.0 | `400c24fb6465` | oci-hermetic `golang@sha256:957861185dbf` |

## Run `nvke-os-amd64-920d6446f814-04`

Lane `unqualified-local-execution`, Plan `sha256:5f430abf1f757c42`.

### Outputs

| Output | Kind | Digest |
|---|---|---|
| `nvke-node-image-amd64` | disk-image | `sha256:f4907b755613825d8f21eeb0ea9d6d9493f71aa7fb8d4deef7b6d8087af567ae` (3,636,723,712 bytes) |

### Components built or acquired

| Component | Source | Version | Commit | Built with |
|---|---|---|---|---|
| `nvke-agent` | dsx-ai-factory/nvke.git | v0.22.0 | `400c24fb6465` | oci-hermetic `sha256:3a7805e2ecd1` |
| `nvke-cni-calico` | dsx-ai-factory/nvke.git | v0.22.0 | `400c24fb6465` | oci-hermetic `sha256:3a7805e2ecd1` |
| `nvke-cni-ovn` | dsx-ai-factory/nvke.git | v0.22.0 | `400c24fb6465` | oci-hermetic `sha256:3a7805e2ecd1` |
| `nvke-image-inputs` | dsx-ai-factory/nvke.git | v0.22.0 | `400c24fb6465` | oci-hermetic `sha256:3a7805e2ecd1` |
| `nvke-kubeadm-distro` | dsx-ai-factory/nvke.git | v0.22.0 | `400c24fb6465` | oci-hermetic `sha256:3a7805e2ecd1` |
| `nvke-node-image-amd64` | dsx-ai-factory/nvke.git | v0.22.0 | `400c24fb6465` | vm-image `sha256:3a7805e2ecd1` |
| `nvke-patched-installer-iso-amd64` | dsx-ai-factory/nvke.git | v0.22.0 | `400c24fb6465` | oci-hermetic `sha256:3a7805e2ecd1` |
| `nvke-spire-agent` | dsx-ai-factory/nvke.git | v0.22.0 | `400c24fb6465` | oci-hermetic `sha256:3a7805e2ecd1` |
| `ovn-kube-ubuntu` | ovn-kubernetes/ovn-kubernetes | v1.4.0 | `d6a3812d1bc1` | buildkit-rootless `moby/buildkit@sha256:80b15f0735e8` |
| `ovn-kubernetes-chart` | ovn-kubernetes/ovn-kubernetes | v1.4.0 | `d6a3812d1bc1` | oci-hermetic `sha256:3a7805e2ecd1` |
| `ubuntu-installer-iso-amd64` | https://releases.ubuntu.com/26.04.1/ubuntu-26.04.1-live-server-amd64.iso | acquired | - | `sha256:cc8a95cde20f6ced` |

### Packer toolchain

Built from `toolchains/nvkr-packer` source locks: packer 1.15.4, qemuPlugin 1.1.6, go 1.27.3, helm 4.2.4, oras 1.3.3, crane 0.21.9, nfpm 2.47.0.
Image ID used by this attempt (amd64): `sha256:3a7805e2ecd11f0a90c7d6be1f5b6620433ce478cc1295d6b85d98a92fa1c86f` (observed and frozen; NVKR keeps no stable pin).

### Packages on the node image

| Package | Version |
|---|---|
| `nvke-agent` | 0.22.0 |
| `nvke-cni-calico-images-3.30.1` | 1 |
| `nvke-cni-calico-manifests-3.30.1` | 1 |
| `nvke-cni-ovn-charts-1.4.0` | 1 |
| `nvke-cni-ovn-images-1.4.0` | 1 |
| `nvke-kubeadm-distro-1.34.2` | 1 |
| `nvke-kubeadm-distro-1.35.3` | 1 |
| `nvke-kubeadm-distro-1.36.3` | 1 |
| `spire-agent` | 1.14.1+tpm1.9.0-4 |

### Kubernetes bundles in `nvke-kubeadm-distro`

| Kubernetes | Bundled with |
|---|---|
| v1.34.2 | containerd v2.1.7, runc v1.3.5, helm v3.20.2, cri-tools v1.34.0 |
| v1.35.3 | containerd v2.2.3, runc v1.3.5, helm v3.20.2, cri-tools v1.35.0 |
| v1.36.3 | containerd v2.3.0, runc v1.4.2, helm v4.1.4, cri-tools v1.36.0 |
