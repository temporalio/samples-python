#!/usr/bin/env bash
# Build the unreleased dependencies of the AgentCore samples into ./wheels/.
#
# TEMPORARY: activity sessions (sticky activities) are not yet in a released
# temporalio, and the plugins' `session_options` argument is not yet in a
# released temporalio-strands-agents / temporalio-openai-agents. Delete this
# script, the wheels/ directory and the `[tool.uv.sources]` entries in each
# sample's pyproject.toml once those releases exist.
#
# Where the sources come from: by default the script clones them from GitHub
# into the gitignored ./.wheel-build/ scratch dir and checks out a ref (branch,
# tag or commit SHA):
#   sdk-python       https://github.com/temporalio/sdk-python.git      dev/sticky-activities
#   ai-integrations  https://github.com/temporalio/ai-integrations.git feature/activity-sessions
# Re-runs reuse the clones (fetch + checkout). sdk-python's sdk-core submodule
# is initialised recursively. Point SDK_PYTHON_DIR / AI_INTEGRATIONS_DIR at a
# local checkout instead to build from it as-is (no clone; the checkout is
# only read, never modified).
#
# Why wheels, and why Linux: `agentcore deploy` (CodeZip) packages the runtime
# on this machine by running
#     uv pip install -r pyproject.toml --target <staging> --python-version 3.12 \
#        --python-platform aarch64-manylinux2014 --only-binary :all:
# (falling back to manylinux_2_28 / _2_34). So every unreleased dependency has
# to exist as a wheel installable on Linux arm64. The plugins are pure Python
# (one py3-none-any wheel each); temporalio has a Rust extension and is built
# in a linux/arm64 manylinux2014 container (same toolchain as the SDK's
# cibuildwheel config). A macOS arm64 temporalio wheel is built too when
# possible; it is only needed for local `uv lock` / `uv sync` / lint / tests on
# macOS, not for deploying.
#
# Why resolution can only pick these builds: each sample pins temporalio and the
# plugin with `[tool.uv.sources]` *path* sources (with sys_platform markers to
# select the Linux or macOS temporalio wheel). uv never consults PyPI for a
# package that has a path source, and `uv pip install -r pyproject.toml` honours
# those sources too. In addition, temporalio is built with the local version
# label `+sessions` (1.34.0+sessions): PyPI cannot host local versions, so the
# build can never be confused with PyPI's temporalio==1.34.0 (in uv's cache, in
# a lock, or in `pip list`), while still satisfying the plugins' `>=1.34.0`.
# The label is applied to a scratch copy of the sources.
#
# The plugin wheels are built with `uv build --no-sources`: ai-integrations
# points its own temporalio dependency at a machine-local wheel path via
# `[tool.uv.sources]`, which does not exist elsewhere. --no-sources ignores it;
# the wheel metadata only says `temporalio>=1.34.0,<2` either way.
#
# Prerequisites: git, uv, and docker able to run linux/arm64 containers
# (native on Apple silicon / arm64 Linux, or via QEMU/binfmt elsewhere).
# Optional: a Rust toolchain (cargo on PATH or in $HOME/.cargo/bin) on macOS,
# for the macOS temporalio wheel. protoc for that wheel is provided by the
# script (protoc-wheel-0 in a cached venv under .wheel-build/), independent of
# any mise/homebrew setup; set PROTOC to use a specific protoc instead.
#
# Usage: ./build-local-wheels.sh            (from anywhere)
# Env overrides:
#   SDK_PYTHON_REPO      (default: https://github.com/temporalio/sdk-python.git)
#   SDK_PYTHON_REF       branch, tag or SHA (default: dev/sticky-activities)
#   AI_INTEGRATIONS_REPO (default: https://github.com/temporalio/ai-integrations.git)
#   AI_INTEGRATIONS_REF  branch, tag or SHA (default: feature/activity-sessions)
#   SDK_CORE_REPO        URL for sdk-python's sdk-core submodule (default: the
#                        URL in sdk-python's .gitmodules, temporalio/sdk-rust);
#                        use when the pinned sdk-core commit lives elsewhere
#   SDK_PYTHON_DIR       use this local sdk-python checkout; skips the clone
#   AI_INTEGRATIONS_DIR  use this local ai-integrations checkout; skips the clone
#   SKIP_LINUX=1 / SKIP_MACOS=1 / SKIP_PLUGINS=1   build a subset
#   MANYLINUX_IMAGE      (default: quay.io/pypa/manylinux2014_aarch64)
#   PROTOC               protoc for the macOS wheel (default: protoc-wheel-0
#                        installed into .wheel-build/protoc-venv)
#   RELOCK=1             afterwards run `uv lock --refresh` in both samples
#                        (needs the macOS wheel; see below)
#
# Example, pinning the SDK to a commit:
#   SDK_PYTHON_REF=e73f54d3 ./build-local-wheels.sh
#
# The resolved commit of each source is written to wheels/BUILD_INFO; include
# it when reporting results.
#
# After rebuilding, the committed uv.lock hashes no longer match. Deploying
# does not use uv.lock, but local `uv sync` does; re-lock with RELOCK=1 or:
#   cd strands_agent && uv lock --refresh && uv sync
# uv.lock covers macOS and Linux, so locking needs both temporalio wheels.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/wheels"
SCRATCH="$HERE/.wheel-build"
LOCAL_LABEL="sessions"
MANYLINUX_IMAGE="${MANYLINUX_IMAGE:-quay.io/pypa/manylinux2014_aarch64}"
SDK_PYTHON_REPO="${SDK_PYTHON_REPO:-https://github.com/temporalio/sdk-python.git}"
SDK_PYTHON_REF="${SDK_PYTHON_REF:-dev/sticky-activities}"
AI_INTEGRATIONS_REPO="${AI_INTEGRATIONS_REPO:-https://github.com/temporalio/ai-integrations.git}"
AI_INTEGRATIONS_REF="${AI_INTEGRATIONS_REF:-feature/activity-sessions}"

mkdir -p "$OUT" "$SCRATCH"

# fetch_source <repo> <ref> <dest> [<submodule path> <name> <url>]: clone <repo> into <dest> (or reuse an
# existing clone), check out <ref> detached, and init submodules recursively.
# A ref naming a remote branch resolves to its freshly fetched tip.
fetch_source() {
  local repo="$1" ref="$2" dest="$3"
  if [[ -d "$dest/.git" ]]; then
    echo "reusing clone $dest (fetching $repo)"
    git -C "$dest" remote set-url origin "$repo"
    git -C "$dest" fetch --tags --force --prune origin
  else
    rm -rf "$dest"
    git clone "$repo" "$dest"
  fi
  local target="$ref"
  if git -C "$dest" rev-parse --verify --quiet "refs/remotes/origin/$ref^{commit}" >/dev/null; then
    target="origin/$ref"
  fi
  if ! git -C "$dest" rev-parse --verify --quiet "$target^{commit}" >/dev/null; then
    echo "error: ref '$ref' not found in $repo" >&2
    exit 1
  fi
  git -C "$dest" -c advice.detachedHead=false checkout --force --detach "$target"
  git -C "$dest" submodule sync --recursive
  # Optional URL override for one submodule (by name), e.g. a fork of sdk-core.
  if [[ -n "${4:-}" ]]; then
    git -C "$dest" submodule init -- "$4"
    git -C "$dest" config "submodule.$5.url" "$6"
    if [[ -e "$dest/$4/.git" ]]; then
      git -C "$dest/$4" remote set-url origin "$6"
    fi
  fi
  git -C "$dest" submodule update --init --recursive --force
}

BUILD_INFO_SOURCES=""
RESOLVED_DIR=""
# resolve_source <name> <local dir or ""> <repo> <ref>: sets RESOLVED_DIR.
# (Not called via $(...), so BUILD_INFO_SOURCES survives.)
resolve_source() {
  local name="$1" dir="$2" repo="$3" ref="$4" sha
  if [[ -n "$dir" ]]; then
    dir="$(cd "$dir" && pwd)"
    sha="$(git -C "$dir" rev-parse HEAD)"
    local dirty=""
    [[ -z "$(git -C "$dir" status --porcelain --untracked-files=no)" ]] || dirty=" (uncommitted changes)"
    BUILD_INFO_SOURCES+="$name: local checkout $dir @ $sha$dirty"$'\n'
  else
    dir="$SCRATCH/src/$name"
    if [[ "$name" == "sdk-python" && -n "${SDK_CORE_REPO:-}" ]]; then
      fetch_source "$repo" "$ref" "$dir" temporalio/bridge/sdk-core sdk-core "$SDK_CORE_REPO"
    else
      fetch_source "$repo" "$ref" "$dir"
    fi
    sha="$(git -C "$dir" rev-parse HEAD)"
    BUILD_INFO_SOURCES+="$name: $repo ref=$ref commit=$sha"$'\n'
    if [[ "$name" == "sdk-python" ]]; then
      BUILD_INFO_SOURCES+="  sdk-core submodule: $(git -C "$dir" config submodule.sdk-core.url) commit=$(git -C "$dir/temporalio/bridge/sdk-core" rev-parse HEAD)"$'\n'
    fi
  fi
  echo "$name: $dir @ $sha"
  RESOLVED_DIR="$dir"
}

NEED_SDK=0
[[ "${SKIP_LINUX:-}" == "1" && "${SKIP_MACOS:-}" == "1" ]] || NEED_SDK=1
if [[ "$NEED_SDK" == "1" ]]; then
  resolve_source sdk-python "${SDK_PYTHON_DIR:-}" "$SDK_PYTHON_REPO" "$SDK_PYTHON_REF"
  SDK_SRC="$RESOLVED_DIR"
fi
if [[ "${SKIP_PLUGINS:-}" != "1" ]]; then
  resolve_source ai-integrations "${AI_INTEGRATIONS_DIR:-}" "$AI_INTEGRATIONS_REPO" "$AI_INTEGRATIONS_REF"
  AI_SRC="$RESOLVED_DIR"
fi

# Copy the SDK sources (tracked files incl. the sdk-core submodule, no build
# output) into $1 and stamp the local version label onto the copy.
stage_sdk() {
  local dest="$1"
  rm -rf "$dest"
  mkdir -p "$dest"
  (cd "$SDK_SRC" && git ls-files -z --recurse-submodules |
    tar -cf - --no-recursion --null -T -) |
    (cd "$dest" && tar -xf -)
  local version
  version="$(sed -n 's/^version = "\(.*\)"$/\1/p' "$dest/pyproject.toml" | head -1)"
  sed -i.bak "s/^version = \"$version\"$/version = \"$version+$LOCAL_LABEL\"/" "$dest/pyproject.toml"
  rm -f "$dest/pyproject.toml.bak"
  echo "staged temporalio $version+$LOCAL_LABEL in $dest"
}

if [[ "${SKIP_LINUX:-}" != "1" ]]; then
  echo "==> temporalio (manylinux2014 aarch64, docker)"
  stage_sdk "$SCRATCH/sdk-linux"
  trap 'rm -rf "$SCRATCH/sdk-linux"' EXIT
  rm -f "$OUT"/temporalio-*manylinux*.whl
  # Named volumes cache rustup, the cargo registry and the target dir across runs.
  docker run --rm --platform linux/arm64 \
    -v "$SCRATCH/sdk-linux:/src" \
    -v "$OUT:/out" \
    -v temporalio-wheel-rustup:/root/.rustup \
    -v temporalio-wheel-cargo:/root/.cargo \
    -v temporalio-wheel-target:/src/temporalio/bridge/target \
    -e CARGO_NET_GIT_FETCH_WITH_CLI=true \
    "$MANYLINUX_IMAGE" bash -euo pipefail -c '
      export PATH="/root/.cargo/bin:/opt/python/cp312-cp312/bin:$PATH"
      command -v rustup >/dev/null || curl -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable --profile minimal
      rustup default stable >/dev/null
      python -m pip install -q "maturin>=1.8.2,<2" protoc-wheel-0
      cd /src
      maturin build --release --compatibility manylinux2014 --interpreter python3.12 --out /out
    '
fi

if [[ "${SKIP_MACOS:-}" != "1" ]]; then
  MACOS_SKIP_HINT="local uv lock/sync, lint and tests on macOS need it; deploying does not"
  if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "==> skipping macOS temporalio wheel (not on macOS)"
  elif ! PATH="$HOME/.cargo/bin:$PATH" command -v cargo >/dev/null; then
    echo "==> skipping macOS temporalio wheel: no Rust toolchain (cargo) found on PATH or in \$HOME/.cargo/bin"
    echo "    ($MACOS_SKIP_HINT; install Rust from https://rustup.rs to build it)"
  else
    echo "==> temporalio (macOS arm64)"
    # protoc: the temporalio-protos build script runs $PROTOC, else `protoc`
    # from PATH. In a mise-activated shell that is a mise shim which refuses to
    # run inside the staged copy (sdk-core's mise.toml is untrusted there). So,
    # like the Linux build, provide our own protoc from protoc-wheel-0 in a
    # cached scratch venv, unless the caller set PROTOC.
    if [[ -z "${PROTOC:-}" ]]; then
      PROTOC_VENV="$SCRATCH/protoc-venv"
      if [[ ! -x "$PROTOC_VENV/bin/protoc" ]]; then
        rm -rf "$PROTOC_VENV"
        uv venv --quiet "$PROTOC_VENV"
        uv pip install --quiet --python "$PROTOC_VENV/bin/python" protoc-wheel-0
      fi
      PROTOC="$PROTOC_VENV/bin/protoc"
    fi
    if ! PROTOC_VERSION="$("$PROTOC" --version 2>&1)"; then
      echo "error: protoc '$PROTOC' does not run: $PROTOC_VERSION" >&2
      exit 1
    fi
    echo "using $PROTOC ($PROTOC_VERSION)"
    stage_sdk "$SCRATCH/sdk-macos"
    rm -f "$OUT"/temporalio-*macosx*.whl
    # A persistent cargo target dir (outside the staged copy) keeps rebuilds incremental.
    # MISE_IGNORED_CONFIG_PATHS: never let mise parse the staged sdk-core mise.toml.
    (cd "$SCRATCH/sdk-macos" &&
      PATH="$HOME/.cargo/bin:$PATH" \
      PROTOC="$PROTOC" \
      MISE_IGNORED_CONFIG_PATHS="${MISE_IGNORED_CONFIG_PATHS:+$MISE_IGNORED_CONFIG_PATHS:}$SCRATCH" \
      MACOSX_DEPLOYMENT_TARGET=11.0 \
      CARGO_TARGET_DIR="$SCRATCH/macos-target" \
      uv build --wheel --out-dir "$OUT")
    rm -rf "$SCRATCH/sdk-macos"
  fi
fi

if [[ "${SKIP_PLUGINS:-}" != "1" ]]; then
  for plugin in strands_agents openai_agents; do
    echo "==> plugin $plugin"
    dist="temporalio_${plugin}"
    rm -f "$OUT/${dist}"-*.whl
    # Pure Python (py3-none-any): one wheel serves macOS and Linux.
    # --no-sources: ignore ai-integrations' machine-local temporalio path source.
    (cd "$AI_SRC/python/$plugin" && uv build --wheel --no-sources --out-dir "$OUT")
  done
fi

{
  echo "built: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '%s' "$BUILD_INFO_SOURCES"
  echo "wheels (sha256):"
  (cd "$OUT" && for w in *.whl; do
    [[ -e "$w" ]] || continue
    if command -v sha256sum >/dev/null; then sha256sum "$w"; else shasum -a 256 "$w"; fi
  done)
} >"$OUT/BUILD_INFO"

if [[ "${RELOCK:-}" == "1" ]]; then
  for sample in strands_agent openai_agent; do
    echo "==> uv lock --refresh ($sample)"
    (cd "$HERE/$sample" && uv lock --refresh)
  done
fi

echo "==> $OUT/BUILD_INFO:"
cat "$OUT/BUILD_INFO"
