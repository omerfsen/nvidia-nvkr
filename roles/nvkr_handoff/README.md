# omerfsen.nvkr.nvkr_handoff

Hands what `omerfsen.nvkr.nvkr_build` (main) built to [omerfsen.nvke](https://github.com/omerfsen/nvke):
the node image copied for libvirt and checked against its Run, the verified nvkectl (it must be the NVKE
release omerfsen.nvke pins), and the two seed-cluster images as OCI archives for `nerdctl load`. Writes
`nvke-vars.yml` for omerfsen.nvke's prebuilt-artifact options:

```shell
ansible-playbook -i inventory/kvm playbooks/kvm.yml -e @/var/lib/nvkr/handoff/nvke-vars.yml
```

Variables: `ansible-doc -t role omerfsen.nvkr.nvkr_handoff`.
