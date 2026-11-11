# omerfsen.nvkr.nvkr

Builds the [NVKR](https://github.com/dsx-ai-factory/nvkr) CLI from a pinned release on a Debian or
Ubuntu host (amd64 or arm64): build packages, Docker with a `docker-container` Buildx builder on a
pinned BuildKit, the exact Go of the release (checksum verified), the checkout (a tag that does not
resolve to `nvkr_commit` fails the run) and `GOTOOLCHAIN=local make build`. Sets `nvkr_bin`.

Include it with `public: true` so the other roles see its variables:

```yaml
- name: NVKR CLI
  ansible.builtin.include_role:
    name: omerfsen.nvkr.nvkr
    public: true
```

Variables: `ansible-doc -t role omerfsen.nvkr.nvkr`, or
[docs/variables.md](https://github.com/omerfsen/nvidia-nvkr/blob/main/docs/variables.md).
