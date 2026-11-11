# omerfsen.nvkr.nvkr_build

Runs NVKR locally after `omerfsen.nvkr.nvkr`. Entry points:

| Entry point | Does |
|---|---|
| `registry` | Local OCI registry (pinned image, loopback) |
| `hello` | NVKR's quickstart example: build, SBOM, publish |
| `components` | nvkectl, `nke-controller` and `cluster-api-provider-provisioned`, built and published |
| `node_image` | The NVKE node image with NVKR's local route; every OCI image blob checked |
| `verify` | Pull a release's outputs and check their digests (not signatures: local Runs are unsigned) |
| `main` | `registry`, `components`, `verify` and `node_image` |

NVKR attempts are immutable: a completed attempt is not run again, a failed one stops the play until
`nvkr_build_attempt_suffixes` names a new one. See
[how it works](https://github.com/omerfsen/nvidia-nvkr/blob/main/docs/how-it-works.md).

Variables: `ansible-doc -t role omerfsen.nvkr.nvkr_build`.
