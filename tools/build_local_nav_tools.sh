#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
recast_root="${EQL_RECAST_ROOT:-$HOME/.local/share/eql-automation/toolchains/recastnavigation}"
build_root="${EQL_RECAST_BUILD_ROOT:-$HOME/.local/share/eql-automation/toolchains/recast-build}"
output_root="${EQL_NAV_TOOLS_ROOT:-$HOME/.local/share/eql-automation/toolchains}"
required_commit=9f4ce64458dfae86e1239c525ddc219c4e9e06f1

if [[ ! -d "$recast_root/.git" ]]; then
    echo "Missing pinned Recast source at $recast_root" >&2
    exit 1
fi
actual_commit="$(git -C "$recast_root" rev-parse HEAD)"
if [[ "$actual_commit" != "$required_commit" ]]; then
    echo "Recast commit mismatch: expected $required_commit, found $actual_commit" >&2
    exit 1
fi
mkdir -p -- "$output_root"
cmake -S "$recast_root" -B "$build_root" -G Ninja \
    -DRECASTNAVIGATION_DEMO=OFF -DRECASTNAVIGATION_TESTS=OFF \
    -DRECASTNAVIGATION_EXAMPLES=OFF -DBUILD_SHARED_LIBS=OFF \
    -DCMAKE_BUILD_TYPE=Release
cmake --build "$build_root" -j "${EQL_BUILD_JOBS:-4}"
g++ -std=c++17 -O2 -Wall -Wextra \
    -I"$recast_root/Recast/Include" -I"$recast_root/Detour/Include" \
    "$project_root/tools/bake_local_navmesh.cpp" \
    "$build_root/Recast/libRecast.a" "$build_root/Detour/libDetour.a" \
    -o "$output_root/eql-bake-local"
g++ -std=c++17 -O2 -Wall -Wextra -I"$recast_root/Detour/Include" \
    "$project_root/tools/query_local_navmesh.cpp" \
    "$build_root/Detour/libDetour.a" -o "$output_root/eql-query-local"
echo "Built $output_root/eql-bake-local and $output_root/eql-query-local"
