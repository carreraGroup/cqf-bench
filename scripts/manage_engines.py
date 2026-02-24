#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

from config_io import load_config


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, capture_output=False)


def selected_engines(doc: dict[str, Any], selected: list[str]) -> list[dict[str, Any]]:
    engines = doc.get("engines", [])
    if not selected:
        return engines
    selected_set = set(selected)
    return [e for e in engines if e["name"] in selected_set]


def docker_enabled(engine: dict[str, Any]) -> bool:
    return bool(engine.get("docker", {}).get("enabled", False))


def env_expand(value: str) -> str:
    out = value
    for key, env_val in os.environ.items():
        out = out.replace(f"${{{key}}}", env_val)
    return out


def image_exists(image: str) -> bool:
    result = subprocess.run(["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"], check=True, text=True, capture_output=True)
    return image in result.stdout.splitlines()


def pull_engine(engine: dict[str, Any]) -> None:
    d = engine["docker"]
    image = d.get("image", "")
    if not image:
        print(f"[{engine['name']}] skip pull: no docker.image")
        return
    print(f"[{engine['name']}] docker pull {image}")
    run(["docker", "pull", image])


def build_engine(engine: dict[str, Any]) -> None:
    d = engine["docker"]
    image = d.get("image", "")
    context = d.get("build_context", "")
    dockerfile = d.get("dockerfile", "Dockerfile")
    build_args = d.get("build_args", {})

    if not image:
        print(f"[{engine['name']}] skip build: no docker.image")
        return
    if not context:
        print(f"[{engine['name']}] skip build: no docker.build_context")
        return

    cmd = [
        "docker",
        "build",
        "-f",
        str(Path(context) / dockerfile),
        "-t",
        image,
    ]
    for k, v in build_args.items():
        cmd.extend(["--build-arg", f"{k}={env_expand(str(v))}"])
    cmd.append(context)

    print(f"[{engine['name']}] {' '.join(cmd)}")
    run(cmd)


def container_exists(name: str) -> bool:
    result = subprocess.run(["docker", "ps", "-a", "--format", "{{.Names}}"], check=True, text=True, capture_output=True)
    names = result.stdout.splitlines()
    return name in names


def up_engine(engine: dict[str, Any]) -> None:
    d = engine["docker"]
    image = d.get("image", "")
    name = d.get("container_name", engine["name"])
    host_port = str(d.get("host_port", ""))
    container_port = str(d.get("container_port", ""))
    env_map = d.get("env", {})

    if not image or not host_port or not container_port:
        print(f"[{engine['name']}] skip up: missing image/ports")
        return

    if container_exists(name):
        print(f"[{engine['name']}] container exists; restarting {name}")
        run(["docker", "rm", "-f", name], check=False)

    cmd = [
        "docker",
        "run",
        "-d",
        "--name",
        name,
        "-p",
        f"{host_port}:{container_port}",
    ]

    for k, v in env_map.items():
        cmd.extend(["-e", f"{k}={env_expand(str(v))}"])

    cmd.append(image)
    print(f"[{engine['name']}] {' '.join(cmd)}")
    run(cmd)


def down_engine(engine: dict[str, Any]) -> None:
    name = engine.get("docker", {}).get("container_name", engine["name"])
    print(f"[{engine['name']}] docker rm -f {name}")
    run(["docker", "rm", "-f", name], check=False)


def status_engine(engine: dict[str, Any]) -> None:
    name = engine.get("docker", {}).get("container_name", engine["name"])
    print(f"[{engine['name']}] status for {name}")
    run(["docker", "ps", "-a", "--filter", f"name={name}"])


def health_engine(engine: dict[str, Any]) -> None:
    base_url = engine.get("base_url", "")
    path = engine.get("docker", {}).get("health_path", "/metadata")
    url = f"{base_url.rstrip('/')}{path}"
    print(f"[{engine['name']}] health GET {url}")
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            print(f"[{engine['name']}] health status={resp.status}")
    except Exception as exc:  # noqa: BLE001
        print(f"[{engine['name']}] health FAILED: {exc}")


def bootstrap_engine(engine: dict[str, Any]) -> None:
    d = engine.get("docker", {})
    image = d.get("image", "")

    if d.get("build_context"):
        build_engine(engine)
    elif d.get("local_image_only", False):
        if not image_exists(image):
            raise RuntimeError(
                f"[{engine['name']}] local image required but missing: {image}. Build it in Mercury repo first."
            )
        print(f"[{engine['name']}] using local image {image}")
    elif d.get("pull_on_bootstrap", True):
        pull_engine(engine)

    up_engine(engine)
    health_engine(engine)


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage benchmark target engines via Docker")
    parser.add_argument("action", choices=["pull", "build", "up", "down", "status", "health", "bootstrap"])
    parser.add_argument("--engines", type=Path, default=Path("bench/config/engines.example.yaml"))
    parser.add_argument("--engine", action="append", default=[], help="Only apply to selected engine name(s)")
    args = parser.parse_args()

    doc = load_config(args.engines)
    engines = selected_engines(doc, args.engine)
    if not engines:
        print("No matching engines")
        return 1

    for e in engines:
        if not docker_enabled(e):
            print(f"[{e['name']}] docker disabled; skipping")
            continue

        if args.action == "pull":
            pull_engine(e)
        elif args.action == "build":
            build_engine(e)
        elif args.action == "up":
            up_engine(e)
        elif args.action == "down":
            down_engine(e)
        elif args.action == "status":
            status_engine(e)
        elif args.action == "health":
            health_engine(e)
        elif args.action == "bootstrap":
            bootstrap_engine(e)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
