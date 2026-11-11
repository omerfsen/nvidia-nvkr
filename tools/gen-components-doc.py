#!/usr/bin/env python3
"""Write docs/components.md: every component version that went into the NVKR
build on this host, read from the build itself, not typed by hand.

Sources: the NVKR CLI and checkout, the newest completed Run of each input set
(its Plan, lifecycle record, frozen inputs and .deb outputs), the Run logs, and
this collection's role defaults. Run on the build host after the playbooks:

    make components            # NVKR_HOME=/var/lib/nvkr by default
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
HOME = Path(os.environ.get("NVKR_HOME", "/var/lib/nvkr"))
PREFIXES = ["hello", "nvke-components", "nvke-os-amd64", "nvke-os-arm64"]


def short(value, n=12):
    value = value or ""
    if value.startswith("sha256:"):
        return "sha256:" + value[7:7 + n]
    if "@sha256:" in value:
        name, digest = value.split("@sha256:", 1)
        return f"{name}@sha256:{digest[:n]}"
    return value[:n] if re.fullmatch(r"[0-9a-f]{40}", value) else value


def defaults(role):
    return yaml.safe_load((ROOT / "roles" / role / "defaults" / "main.yml").read_text())


def newest_complete(runs_roots, prefix):
    best = None
    for runs in runs_roots:
        if not runs.is_dir():
            continue
        for attempt in runs.iterdir():
            record = attempt / "lifecycle.json"
            if not attempt.name.startswith(prefix + "-") or not record.is_file():
                continue
            data = json.loads(record.read_text())
            if data.get("status") != "complete":
                continue
            if best is None or record.stat().st_mtime > best[0]:
                best = (record.stat().st_mtime, attempt, data)
    return best


def deb_versions(attempt):
    seen = {}
    for deb in sorted(attempt.rglob("*.deb")):
        try:
            out = subprocess.run(["dpkg-deb", "-f", str(deb), "Package", "Version"],
                                 capture_output=True, text=True, check=True).stdout
        except (OSError, subprocess.CalledProcessError):
            continue
        fields = dict(line.split(": ", 1) for line in out.strip().splitlines() if ": " in line)
        if "Package" in fields:
            seen[fields["Package"]] = fields.get("Version", "")
    return seen


def main():
    nvkr_d = defaults("nvkr")
    build_d = defaults("nvkr_build")
    src = HOME / "src" / f"nvkr-{nvkr_d['nvkr_version']}"
    nvkr_bin = src / "bin" / "nvkr"
    version = subprocess.run([str(nvkr_bin), "--version"], capture_output=True, text=True).stdout.strip()
    runs_roots = [src / ".nvkr" / "runs"] + [p / ".nvkr" / "runs" for p in (src / ".nvkr" / "omerfsen").glob("hello-*")]

    out = [
        "# Components",
        "",
        "Every component version that went into the NVKR build on the build machine,",
        "read from the build itself by `make components` (`tools/gen-components-doc.py`):",
        "the NVKR CLI, the Plans and records of the newest completed Runs, their",
        "packages and logs, and this collection's role defaults. Regenerate it after",
        "an NVKR bump or a new build.",
        "",
        "## NVKR and this collection's pins",
        "",
        "| Component | Version | Pinned in |",
        "|---|---|---|",
        f"| NVKR CLI | `{version}` | `nvkr_version`, `nvkr_commit` (`{nvkr_d['nvkr_commit']}`) |",
        f"| Go for the CLI | {(src / '.go-version').read_text().strip()} (NVKR's `.go-version`) | `nvkr_go_version`, `nvkr_go_sha256` |",
        f"| BuildKit for the Packer toolchain build | `{short(nvkr_d['nvkr_buildkit_image'])}` | `nvkr_buildkit_image` |",
        f"| Local registry | `{short(build_d['nvkr_build_registry_image'])}` | `nvkr_build_registry_image` |",
        "",
    ]

    for prefix in PREFIXES:
        found = newest_complete(runs_roots, prefix)
        if not found:
            continue
        _, attempt, record = found
        plan = json.loads((attempt / ".runner" / "plan.json").read_text())
        out += [f"## Run `{attempt.name}`", "",
                f"Lane `{record['lane']}`, Plan `{short(record.get('planDigest'), 16)}`.", ""]
        out += ["### Outputs", "", "| Output | Kind | Digest |", "|---|---|---|"]
        for obs in record["observed"]:
            size = obs.get("disk", {}).get("size")
            extra = f" ({size:,} bytes)" if size else ""
            out.append(f"| `{obs['name']}` | {obs['kind']} | `{obs['digest']}`{extra} |")
        out += ["", "### Components built or acquired", "",
                "| Component | Source | Version | Commit | Built with |", "|---|---|---|---|---|"]
        for build in plan["builds"]:
            arch = build.get("platform", "linux/amd64").split("/")[-1]
            for comp in build["resolvedComponents"]:
                if comp.get("prebuilt"):
                    pre = comp["prebuilt"]
                    out.append(f"| `{comp['Name']}` | {pre.get('url', '')} | acquired | - | "
                               f"`{short(pre.get('digests', {}).get(arch, ''), 16)}` |")
                    continue
                image = comp.get("toolchainImage") or (comp.get("toolchainImages") or {}).get(arch, "")
                repo = (comp.get("repo") or "").replace("https://github.com/", "")
                out.append(f"| `{comp['Name']}` | {repo} | {comp.get('tag', '')} | `{short(comp.get('commit'))}` | "
                           f"{comp.get('builderType', '')} `{short(image)}` |")
        out.append("")

        if prefix.startswith("nvke-os-"):
            frozen = src / ".nvkr" / "inputs" / attempt.name / "toolchain-attempt.json"
            lock = json.loads((src / "toolchains" / "nvkr-packer" / "toolchain.lock.json").read_text())
            tools = [f"{k} {v['version']}" for k, v in lock.items() if isinstance(v, dict) and "version" in v]
            out += ["### Packer toolchain", "",
                    f"Built from `toolchains/nvkr-packer` source locks: {', '.join(tools)}."]
            if frozen.is_file():
                subs = json.loads(frozen.read_text()).get("toolchainSubstitutions", [])
                for sub in subs:
                    out.append(f"Image ID used by this attempt ({sub.get('arch')}): `{sub.get('to')}` "
                               "(observed and frozen; NVKR keeps no stable pin).")
            out.append("")
            debs = deb_versions(attempt)
            if debs:
                out += ["### Packages on the node image", "", "| Package | Version |", "|---|---|"]
                out += [f"| `{name}` | {ver} |" for name, ver in sorted(debs.items())]
                out.append("")
            log = HOME / "logs" / f"{attempt.name}.log"
            if log.is_file():
                bundles = sorted(set(re.findall(r"bundle\.sh: (v\d+\.\d+\.\d+) \(([^)]*)\)", log.read_text(errors="replace"))))
                if bundles:
                    out += ["### Kubernetes bundles in `nvke-kubeadm-distro`", "",
                            "| Kubernetes | Bundled with |", "|---|---|"]
                    out += [f"| {k8s} | {rest} |" for k8s, rest in bundles]
                    out.append("")

    (ROOT / "docs" / "components.md").write_text("\n".join(out).rstrip() + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
