# Lab: from pinned source to a GPU cluster with NVKR, NVKE and AICR

A step-by-step lab you can follow, or record. Each step has what to say, what
to run and what you should see; the outputs are from a real run on the build
machine. Plan about 90 minutes of machine time: most of it is the node image
(about 15 minutes with a warm cache, longer the first time) and the cluster
bootstrap (about 20 minutes).

**The story:** NVIDIA Kubernetes Recipes (NVKR) builds NVIDIA Kubernetes Engine
(NVKE) from pinned source and records what went into every artifact. NVKE
installs clusters. AI Cluster Runtime (AICR) puts the GPU stack on them. This
lab chains the three on one machine: NVKR builds nvkectl, the two seed-cluster
images and the node OS image; NVKE boots its management cluster from exactly
those; AICR makes the GPU usable.

> NVKR, NVKE and AICR are previews and not recommended for production. This is
> an independent community project, not affiliated with or endorsed by NVIDIA.

## 0. What you need

- One Ubuntu 24.04 (or Debian) amd64 host with KVM and Docker, about 32 CPUs'
  worth of patience: 24 cores, 92 GiB of memory and 200 GiB free worked here.
- For the GPU part: one NVIDIA GPU you can pass through (VFIO), here an RTX
  4080 SUPER. Without one, set `nvke_kvm_gpu_devices: []` in omerfsen.nvke and
  skip step 8's GPU checks.
- Python 3.12, Git, and sudo.

## 1. Get the collection

Say: "Everything is an Ansible collection; `make dev` gives it a virtualenv and
links it as omerfsen.nvkr."

```shell
git clone https://github.com/omerfsen/nvidia-nvkr.git
cd nvidia-nvkr
make dev PYTHON=python3.12
```

## 2. The quickstart: NVKR's hello example

Say: "Before NVKE, the smallest thing NVKR can build. We pin a tiny source
repository, build it in a pinned container, publish it to a local registry,
pull it back and check every digest."

```shell
.venv/bin/ansible-playbook playbooks/quickstart.yml
```

You should see, at the end:

```text
msg: Hello, team! This is hello v1.0.0, built by NVKR. (127.0.0.1:5000/hello/releases@sha256:1d5ffc82c27b0c35f86892dc6a6cf66e18a719d0cbe95a5a39a94173b98c05a6)
localhost : ok=73   changed=16   unreachable=0    failed=0
```

Show what NVKR published and how it links the binary to its SBOM:

```shell
N=/var/lib/nvkr/src/nvkr-v0.1.0/bin/nvkr
$N release browse --reference 127.0.0.1:5000/hello/releases@sha256:1d5ffc82c27b0c35f86892dc6a6cf66e18a719d0cbe95a5a39a94173b98c05a6 --anonymous --plain-http
```

```text
Inspection: metadata inspection; payloads, signatures and policy not verified
Outputs: 1 of 1
hello (executable linux/amd64)
  Component: hello @ sha256:7693520e…
  Evidence: sbom-… (hello, build-output)
    Subject: file sha256:7693520e…
```

Run it again: nothing changes.

```text
localhost : ok=69   changed=0    unreachable=0    failed=0
```

Point out: two fresh builds on this machine published the same release digest.

## 3. Look at the node image before building it

Say: "A node image is not one build: the agent, Calico, OVN, the Kubernetes
packages, the SPIRE agent and a patched Ubuntu ISO are each built first, then
NVKE's Packer project turns them into a disk. NVKR can show that graph without
starting anything."

```shell
cd /var/lib/nvkr/src/nvkr-v0.1.0
bin/nvkr run plan --definition inputs/definitions/diagnostics/os-amd64.yaml \
  --environment inputs/environments/local-linux-amd64-kvm.yaml --json > /tmp/os-plan.json
bin/nvkr run graph --plan /tmp/os-plan.json --view producers --format mermaid > /tmp/os-materials.mmd
cd -
```

Open `/tmp/os-materials.mmd` in a Mermaid viewer: `nvke-node-image-amd64` at the
root, its materials below it.

## 3b. Build the NVKE outputs

Say: "Now the real thing. One Run builds nvkectl and the two images NVKE's
bootstrap side-loads, from NVKE v0.22.0 source. A second Run builds the node OS
image: NVKE's own Packer recipe, fed by NVKR-built packages."

```shell
.venv/bin/ansible-playbook playbooks/nvke_release.yml
```

The components (about 2 minutes):

```text
'components release: 127.0.0.1:5000/nvke/releases@sha256:ea027f5f55b05328cc34af02da44c121f85fc4eed7f3ae90b883ea1299c0089d'
```

The node image (about 14 minutes with a warm toolchain cache) ends with the
Run record:

```shell
jq '{attempt, status, lane, disk: .observed[0].disk}' \
  /var/lib/nvkr/src/nvkr-v0.1.0/.nvkr/runs/nvke-os-amd64-*-04/lifecycle.json
```

```text
"status": "complete",
"lane": "unqualified-local-execution",
"disk": { "format": "qcow2", "encryption": "none", "size": 3636723712,
          "payloadDigest": "sha256:f4907b755613825d8f21eeb0ea9d6d9493f71aa7fb8d4deef7b6d8087af567ae" }
```

Say: "Note the lane: unqualified local execution. A local Run is unsigned, and
NVKR keeps disks with their Run instead of publishing them. Signed releases come
from NVKR's GitHub Actions pipeline."

## 4. Check the pinned nvkectl

```shell
/var/lib/nvkr/verified/*/nvkectl/nvkectl version
```

```text
nvkectl v0.22.0 (commit: 400c24fb6465b042be883d6b62472528520d6291, built: 2026-10-21T02:06:38Z)
```

Say: "Same commit omerfsen.nvke pins. The node image is built from that commit too."

## 5. Hand the outputs to NVKE

```shell
.venv/bin/ansible-playbook playbooks/handoff.yml
cat /var/lib/nvkr/handoff/nvke-vars.yml
```

```yaml
node_image_file: /var/lib/libvirt/images/nvke-node-image-amd64-nvkr-f4907b755613.qcow2
nvke_cni_version: 1.4.0
nvke_nvkectl_file: /var/lib/nvkr/verified/ea027f5f55b05328/nvkectl/nvkectl
nvke_controller_image_archive: /var/lib/nvkr/handoff/images/nke-controller-f1d658b5301f-c6f3e2b3.oci.tar
nvke_controller_image: nvkr.local/nvke/nke-controller:nvkr-f1d658b5301f
nvke_provisioned_image_archive: /var/lib/nvkr/handoff/images/cluster-api-provider-provisioned-f34d941093e8-326c3cd0.oci.tar
nvke_provisioned_image: nvkr.local/nvke/cluster-api-provider-provisioned:nvkr-f34d941093e8
```

Say: "Every name carries the digest of what NVKR built: the disk copy is checked
against the Run, and the image archives are made from the pulled and checked
layouts. `nvke_cni_version` is the OVN-Kubernetes version NVKR's image stages."

## 6. Give the GPU to the VMs

In omerfsen.nvke, with its `inventory/kvm/group_vars/all/local.yml` set for this
machine (`nvke_kvm_gpu_devices`, `nvke_kvm_gpu_passthrough_mode: permanent`):

```shell
cd ../nvke
.venv/bin/ansible-playbook -i inventory/kvm playbooks/gpu_passthrough.yml   # stops at a "reboot first" gate
sudo reboot
lspci -nnk -s 01:00     # after the reboot: Kernel driver in use: vfio-pci
```

## 7. Boot the NVKE cluster from the NVKR outputs

```shell
.venv/bin/ansible-playbook -i inventory/kvm playbooks/kvm.yml -e @/var/lib/nvkr/handoff/nvke-vars.yml
```

Watch for these lines, which show NVKE using NVKR's artifacts:

```text
TASK [omerfsen.nvke.node_image : Use the prebuilt image] ... ok
TASK [omerfsen.nvke.nvke : Install the prebuilt nvkectl] ... changed
TASK [omerfsen.nvke.nvke : Load the prebuilt seed-cluster images] ... changed
TASK [omerfsen.nvke.nvke : The prebuilt images loaded under their references] ... ok
```

About 9 minutes later (the real run: `failed=0` on all five hosts):

```shell
export KUBECONFIG=~/.kube/nvke-mgmt.yaml
kubectl get nodes -o wide
```

```text
NAME                    STATUS   ROLES           VERSION   INTERNAL-IP      OS-IMAGE             KERNEL-VERSION              CONTAINER-RUNTIME
nvke-mgmt-cp-0217e043   Ready    control-plane   v1.36.3   192.168.90.103   Ubuntu 26.04.1 LTS   7.0.0-1025-nvidia (amd64)   containerd://2.3.0
nvke-mgmt-cp-717e6a77   Ready    control-plane   v1.36.3   192.168.90.101   Ubuntu 26.04.1 LTS   7.0.0-1025-nvidia (amd64)   containerd://2.3.0
nvke-mgmt-cp-9c83cbc0   Ready    control-plane   v1.36.3   192.168.90.102   Ubuntu 26.04.1 LTS   7.0.0-1025-nvidia (amd64)   containerd://2.3.0
```

The API answers on the VIP, which kube-vip announces over BGP to the
hypervisor: `ip route get 10.250.0.10` shows it via a node.

Prove the nodes run NVKR's image, not omerfsen.nvke's own Packer image: NVKR
v0.1.0's catalog stages upstream OVN-Kubernetes 1.4.0 (NVKE's own image has
2.4.2), and the local package index was written during tonight's Run.

```shell
ssh -i ~/.ssh/nvke/nvke-cp-01_ed25519 ubuntu@192.168.90.101 \
  "dpkg -l 'nvke-*' spire-agent | awk '/^ii/ {print \$2, \$3}'; stat -c %y /usr/lib/nvke/debs/Packages"
```

```text
nvke-agent 0.22.0
nvke-cni-calico-manifests-3.30.1 1
nvke-cni-ovn-charts-1.4.0 1
nvke-cni-ovn-images-1.4.0 1
nvke-kubeadm-distro-1.36.3 1
spire-agent 1.14.1+tpm1.9.0-4
2026-11-10 21:59:44.886563062 +0000
```

The bootstrap VM runs NVKR's nvkectl and seed images:

```shell
ssh -i ~/.ssh/nvke/nvke-bootstrap_ed25519 ubuntu@192.168.90.100 'sudo nerdctl images | grep nvkr.local; sha256sum /usr/local/bin/nvkectl'
sha256sum /var/lib/nvkr/verified/*/nvkectl/nvkectl
```

```text
nvkr.local/nvke/cluster-api-provider-provisioned   nvkr-f34d941093e8   f34d941093e8
nvkr.local/nvke/nke-controller                     nvkr-f1d658b5301f   f1d658b5301f
4a5ea3f8dffe6ceb…  /usr/local/bin/nvkectl
4a5ea3f8dffe6ceb…  /var/lib/nvkr/verified/ea027f5f55b05328/nvkectl/nvkectl
```

And the OVN image on a node is the manifest NVKR built.

```shell
tar -xOf /var/lib/nvkr/src/nvkr-v0.1.0/.nvkr/runs/nvke-os-amd64-*-04/nvke-node-image-amd64/out/ovn-kube-ubuntu/ovn-kube-ubuntu.oci.tar index.json | jq -r '.manifests[0].digest'
ssh -i ~/.ssh/nvke/nvke-cp-01_ed25519 ubuntu@192.168.90.101 'sudo ctr -n k8s.io images ls | grep ovn-kube-ubuntu'
```

```text
NVKR built: sha256:425ad9c6296e0742183cb0128f9cd9168478d5b3f920cb162279b785530df2b1
on node:    sha256:425ad9c6296e0742183cb0128f9cd9168478d5b3f920cb162279b785530df2b1
```

And the GPU node sees the card:

```text
$ ssh -i ~/.ssh/nvke/nvke-cp-03_ed25519 ubuntu@192.168.90.103 'lspci -nn | grep -i nvidia'
05:00.0 VGA compatible controller [0300]: NVIDIA Corporation AD103 [GeForce RTX 4080 SUPER] [10de:2702] (rev a1)
```

Note: the node image's OVN-Kubernetes is upstream 1.4.0 (see the README's known
gaps), so the handoff sets `nvke_cni_version: 1.4.0` and omerfsen.nvke puts it
in the site spec.

## 8. The GPU runtime with AICR

Say: "The cluster has a GPU node but no GPU runtime yet. AICR installs NVIDIA's
GPU Operator stack for this cluster, then validates it."

```shell
cd ../aicr
.venv/bin/ansible-playbook -i ../nvke/inventory/kvm playbooks/nvke.yml -e @examples/nvke-kvm.yml
```

About 9 minutes, `failed=0`. The driver builds inside the GPU node, so the
toolkit and device plugin pods wait in `Init` for a few minutes; `dcgm-exporter`
may restart once while DCGM starts. Then:

```shell
kubectl get nodes -L nvidia.com/gpu.product,nvidia.com/gpu.count
```

```text
NAME                    STATUS   ROLES           VERSION   GPU.PRODUCT                     GPU.COUNT
nvke-mgmt-cp-0217e043   Ready    control-plane   v1.36.3   NVIDIA-GeForce-RTX-4080-SUPER   1
```

AICR's own validation (`/var/lib/aicr/validation.yaml` on the bootstrap VM):
`dra-support`, `gpu-operator-health` and `platform-health` passed, 3 of 3.

Run real GPU work, omerfsen.nvke's test jobs:

```shell
cd ../nvke && KUBECONFIG=~/.kube/nvke-mgmt.yaml bash tests/gpu/run.sh
```

```text
==> summary
    01-gpu-nvidia-smi            PASS        20s
    02-gpu-cuda-vectoradd        PASS        10s
    03-gpu-tensorflow            PASS       101s
    04-gpu-pytorch               PASS        60s
    05-gpu-tensorrt              PASS       111s
    06-gpu-operator-metrics      PASS        10s
```

Run everything again: handoff, nvke and aicr each report `changed=0`.

## 9. Clean up

```shell
cd ../nvke && .venv/bin/ansible-playbook -i inventory/kvm playbooks/kvm_destroy.yml -e nvke_kvm_destroy_confirm=yes
docker rm -f nvkr-registry
```

The NVKR attempts under `/var/lib/nvkr/src/nvkr-v0.1.0/.nvkr/runs/` are the
record of what was built; keep them as long as the cluster runs.
