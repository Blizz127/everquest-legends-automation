// Offline Detour query against a provisional local bake. Never game movement.
#include <DetourAlloc.h>
#include <DetourNavMesh.h>
#include <DetourNavMeshQuery.h>

#include <cmath>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
float read_float(const char* text) {
    std::size_t used = 0;
    const std::string source(text);
    const float value = std::stof(source, &used);
    if (used != source.size() || !std::isfinite(value))
        throw std::runtime_error("invalid query coordinate");
    return value;
}

float point_distance(const float* a, const float* b) {
    const float dx = a[0] - b[0];
    const float dy = a[1] - b[1];
    const float dz = a[2] - b[2];
    return std::sqrt(dx * dx + dy * dy + dz * dz);
}
}

int main(int argc, char** argv) {
    try {
        if (argc != 8) {
            throw std::runtime_error(
                "usage: query_local_navmesh INPUT.nav START_X START_Y START_Z END_X END_Y END_Z");
        }
        std::ifstream input(argv[1], std::ios::binary | std::ios::ate);
        if (!input) throw std::runtime_error("cannot open provisional nav data");
        const std::streamsize size = input.tellg();
        if (size <= 0 || size > 100 * 1024 * 1024) {
            throw std::runtime_error("nav data size is outside safety limit");
        }
        input.seekg(0);
        unsigned char* data = static_cast<unsigned char*>(dtAlloc(size, DT_ALLOC_PERM));
        if (!data) throw std::runtime_error("cannot allocate nav data");
        if (!input.read(reinterpret_cast<char*>(data), size)) {
            dtFree(data);
            throw std::runtime_error("cannot read nav data");
        }
        dtNavMesh* nav = dtAllocNavMesh();
        if (!nav) {
            dtFree(data);
            throw std::runtime_error("cannot allocate Detour mesh");
        }
        const dtStatus init_status = nav->init(data, static_cast<int>(size), DT_TILE_FREE_DATA);
        if (dtStatusFailed(init_status)) {
            dtFree(data);
            dtFreeNavMesh(nav);
            throw std::runtime_error("Detour rejected nav data");
        }
        dtNavMeshQuery* query = dtAllocNavMeshQuery();
        if (!query || dtStatusFailed(query->init(nav, 2048))) {
            if (query) dtFreeNavMeshQuery(query);
            dtFreeNavMesh(nav);
            throw std::runtime_error("cannot initialize Detour query");
        }
        const float start[] = {-read_float(argv[2]), read_float(argv[4]), read_float(argv[3])};
        const float end[] = {-read_float(argv[5]), read_float(argv[7]), read_float(argv[6])};
        const float extents[] = {20.0f, 20.0f, 20.0f};
        dtQueryFilter filter;
        filter.setIncludeFlags(1);
        dtPolyRef start_ref = 0;
        dtPolyRef end_ref = 0;
        float nearest_start[3]{};
        float nearest_end[3]{};
        const dtStatus start_status = query->findNearestPoly(start, extents, &filter,
                                                             &start_ref, nearest_start);
        const dtStatus end_status = query->findNearestPoly(end, extents, &filter,
                                                           &end_ref, nearest_end);
        dtPolyRef corridor[256]{};
        int corridor_count = 0;
        dtStatus path_status = DT_FAILURE;
        float straight[256 * 3]{};
        unsigned char straight_flags[256]{};
        dtPolyRef straight_refs[256]{};
        int straight_count = 0;
        if (dtStatusSucceed(start_status) && dtStatusSucceed(end_status) &&
            start_ref && end_ref) {
            path_status = query->findPath(start_ref, end_ref,
                                          nearest_start, nearest_end, &filter,
                                          corridor, &corridor_count, 256);
            if (dtStatusSucceed(path_status) && corridor_count > 0) {
                query->findStraightPath(nearest_start, nearest_end,
                                        corridor, corridor_count, straight,
                                        straight_flags, straight_refs,
                                        &straight_count, 256);
            }
        }
        const bool complete = dtStatusSucceed(path_status) &&
                              corridor_count > 0 && corridor[corridor_count - 1] == end_ref;
        std::cout << "{\"start_poly_found\":" << (start_ref ? "true" : "false")
                  << ",\"end_poly_found\":" << (end_ref ? "true" : "false")
                  << ",\"start_snap_distance\":";
        if (start_ref) std::cout << point_distance(start, nearest_start);
        else std::cout << "null";
        std::cout << ",\"end_snap_distance\":";
        if (end_ref) std::cout << point_distance(end, nearest_end);
        else std::cout << "null";
        std::cout
                  << ",\"corridor_polygons\":" << corridor_count
                  << ",\"straight_points\":" << straight_count
                  << ",\"offline_path_complete\":" << (complete ? "true" : "false")
                  << ",\"real_client_accepted\":false,\"movement_verified\":false}\n";
        dtFreeNavMeshQuery(query);
        dtFreeNavMesh(nav);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "query_local_navmesh: " << error.what() << '\n';
        return 1;
    }
}
