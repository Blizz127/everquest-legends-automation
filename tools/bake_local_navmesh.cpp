// Offline, bounded Recast bake from a provisional WLD-XYZ OBJ.
// No game input or route acceptance. Requires pinned upstream Recast/Detour.
#include <DetourAlloc.h>
#include <DetourNavMeshBuilder.h>
#include <Recast.h>

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
constexpr int kMaxVertices = 2000000;
constexpr int kMaxFaces = 2000000;
constexpr float kCellSize = 1.0f;
constexpr float kCellHeight = 0.5f;
constexpr float kAgentHeight = 8.0f;
constexpr float kAgentRadius = 5.0f;
constexpr float kAgentClimb = 2.0f;
constexpr float kSlopeDegrees = 45.0f;

struct Vertex { float x, y, z; }; // WLD XYZ, Z up.
struct Face { int a, b, c; };

float read_float(const char* text) {
    const float value = std::stof(text);
    if (!std::isfinite(value)) throw std::runtime_error("nonfinite argument");
    return value;
}

void read_obj(const std::string& path, std::vector<Vertex>& vertices,
              std::vector<Face>& faces) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("cannot read candidate OBJ");
    std::string line;
    while (std::getline(input, line)) {
        if (line.rfind("v ", 0) == 0) {
            std::istringstream row(line.substr(2));
            Vertex vertex{};
            if (!(row >> vertex.x >> vertex.y >> vertex.z) ||
                !std::isfinite(vertex.x) || !std::isfinite(vertex.y) ||
                !std::isfinite(vertex.z)) {
                throw std::runtime_error("invalid OBJ vertex");
            }
            vertices.push_back(vertex);
            if (vertices.size() > kMaxVertices) throw std::runtime_error("OBJ vertex limit exceeded");
        } else if (line.rfind("f ", 0) == 0) {
            std::istringstream row(line.substr(2));
            Face face{};
            if (!(row >> face.a >> face.b >> face.c) ||
                face.a < 1 || face.b < 1 || face.c < 1 ||
                face.a > static_cast<int>(vertices.size()) ||
                face.b > static_cast<int>(vertices.size()) ||
                face.c > static_cast<int>(vertices.size())) {
                throw std::runtime_error("invalid OBJ face indices");
            }
            --face.a; --face.b; --face.c;
            faces.push_back(face);
            if (faces.size() > kMaxFaces) throw std::runtime_error("OBJ face limit exceeded");
        } else if (!line.empty() && line[0] != '#') {
            throw std::runtime_error("unsupported OBJ record");
        }
    }
    if (vertices.empty() || faces.empty()) throw std::runtime_error("candidate OBJ is empty");
}

bool overlaps(const Face& face, const std::vector<Vertex>& vertices,
              float center_x, float center_y, float half_extent) {
    const Vertex& a = vertices[face.a];
    const Vertex& b = vertices[face.b];
    const Vertex& c = vertices[face.c];
    const float min_x = std::min({a.x, b.x, c.x});
    const float max_x = std::max({a.x, b.x, c.x});
    const float min_y = std::min({a.y, b.y, c.y});
    const float max_y = std::max({a.y, b.y, c.y});
    return max_x >= center_x - half_extent && min_x <= center_x + half_extent &&
           max_y >= center_y - half_extent && min_y <= center_y + half_extent;
}
}

int main(int argc, char** argv) {
    try {
        if (argc != 9) {
            throw std::runtime_error(
                "usage: bake_local_navmesh INPUT.obj OUTPUT.nav CENTER_X CENTER_Y HALF_EXTENT MIN_Z MAX_Z LABEL");
        }
        const std::string input_path = argv[1];
        const std::string output_path = argv[2];
        const float center_x = read_float(argv[3]);
        const float center_y = read_float(argv[4]);
        const float half_extent = read_float(argv[5]);
        const float min_z = read_float(argv[6]);
        const float max_z = read_float(argv[7]);
        const std::string label = argv[8];
        const bool label_valid = !label.empty() && label.size() <= 64 &&
            std::all_of(label.begin(), label.end(), [](unsigned char value) {
                return std::isalnum(value) || value == '-' || value == '_';
            });
        if (half_extent < 16 || half_extent > 512 || max_z <= min_z ||
            max_z - min_z > 1000 || !label_valid) {
            throw std::runtime_error("invalid bounded-bake parameters");
        }
        std::vector<Vertex> source_vertices;
        std::vector<Face> source_faces;
        read_obj(input_path, source_vertices, source_faces);
        std::vector<float> vertices;
        vertices.reserve(source_vertices.size() * 3);
        for (const Vertex& vertex : source_vertices) {
            // Lantern's orientation-preserving WLD XYZ -> Recast Y-up basis.
            vertices.push_back(-vertex.x);
            vertices.push_back(vertex.z);
            vertices.push_back(vertex.y);
        }
        std::vector<int> triangles;
        triangles.reserve(source_faces.size() * 3);
        for (const Face& face : source_faces) {
            if (!overlaps(face, source_vertices, center_x, center_y, half_extent)) continue;
            triangles.insert(triangles.end(), {face.a, face.b, face.c});
        }
        const int triangle_count = static_cast<int>(triangles.size() / 3);
        if (triangle_count == 0) throw std::runtime_error("no candidate faces overlap region");

        rcConfig config{};
        config.cs = kCellSize;
        config.ch = kCellHeight;
        config.walkableSlopeAngle = kSlopeDegrees;
        config.walkableHeight = static_cast<int>(std::ceil(kAgentHeight / config.ch));
        config.walkableClimb = static_cast<int>(std::floor(kAgentClimb / config.ch));
        config.walkableRadius = static_cast<int>(std::ceil(kAgentRadius / config.cs));
        config.maxEdgeLen = static_cast<int>(12.0f / config.cs);
        config.maxSimplificationError = 1.3f;
        config.minRegionArea = 8 * 8;
        config.mergeRegionArea = 20 * 20;
        config.maxVertsPerPoly = 6;
        config.detailSampleDist = 6 * config.cs;
        config.detailSampleMaxError = config.ch;
        config.bmin[0] = -(center_x + half_extent);
        config.bmin[1] = min_z;
        config.bmin[2] = center_y - half_extent;
        config.bmax[0] = -(center_x - half_extent);
        config.bmax[1] = max_z;
        config.bmax[2] = center_y + half_extent;
        rcCalcGridSize(config.bmin, config.bmax, config.cs,
                       &config.width, &config.height);
        if (config.width < 1 || config.height < 1 ||
            static_cast<long long>(config.width) * config.height > 1100000) {
            throw std::runtime_error("Recast grid exceeds local-bake safety limit");
        }

        rcContext context(false);
        std::unique_ptr<rcHeightfield, decltype(&rcFreeHeightField)> heightfield(
            rcAllocHeightfield(), rcFreeHeightField);
        if (!heightfield || !rcCreateHeightfield(&context, *heightfield,
                config.width, config.height, config.bmin, config.bmax,
                config.cs, config.ch)) {
            throw std::runtime_error("Recast heightfield creation failed");
        }
        std::vector<unsigned char> areas(triangle_count, 0);
        rcMarkWalkableTriangles(&context, config.walkableSlopeAngle,
                                vertices.data(), static_cast<int>(source_vertices.size()),
                                triangles.data(), triangle_count, areas.data());
        const int marked_walkable = static_cast<int>(std::count_if(
            areas.begin(), areas.end(), [](unsigned char area) { return area != 0; }));
        if (!rcRasterizeTriangles(&context, vertices.data(),
                                  static_cast<int>(source_vertices.size()),
                                  triangles.data(), areas.data(), triangle_count,
                                  *heightfield, config.walkableClimb)) {
            throw std::runtime_error("Recast rasterization failed");
        }
        rcFilterLowHangingWalkableObstacles(&context, config.walkableClimb, *heightfield);
        rcFilterLedgeSpans(&context, config.walkableHeight, config.walkableClimb, *heightfield);
        rcFilterWalkableLowHeightSpans(&context, config.walkableHeight, *heightfield);

        std::unique_ptr<rcCompactHeightfield, decltype(&rcFreeCompactHeightfield)> compact(
            rcAllocCompactHeightfield(), rcFreeCompactHeightfield);
        if (!compact || !rcBuildCompactHeightfield(&context,
                config.walkableHeight, config.walkableClimb, *heightfield, *compact)) {
            throw std::runtime_error("Recast compact heightfield failed");
        }
        if (!rcErodeWalkableArea(&context, config.walkableRadius, *compact) ||
            !rcBuildRegionsMonotone(&context, *compact, 0,
                                    config.minRegionArea, config.mergeRegionArea)) {
            throw std::runtime_error("Recast region build failed");
        }
        std::unique_ptr<rcContourSet, decltype(&rcFreeContourSet)> contours(
            rcAllocContourSet(), rcFreeContourSet);
        if (!contours || !rcBuildContours(&context, *compact,
                config.maxSimplificationError, config.maxEdgeLen, *contours)) {
            throw std::runtime_error("Recast contour build failed");
        }
        std::unique_ptr<rcPolyMesh, decltype(&rcFreePolyMesh)> poly_mesh(
            rcAllocPolyMesh(), rcFreePolyMesh);
        if (!poly_mesh || !rcBuildPolyMesh(&context, *contours,
                config.maxVertsPerPoly, *poly_mesh) || poly_mesh->npolys < 1) {
            throw std::runtime_error("Recast polygon mesh is empty or invalid");
        }
        std::unique_ptr<rcPolyMeshDetail, decltype(&rcFreePolyMeshDetail)> detail(
            rcAllocPolyMeshDetail(), rcFreePolyMeshDetail);
        if (!detail || !rcBuildPolyMeshDetail(&context, *poly_mesh, *compact,
                config.detailSampleDist, config.detailSampleMaxError, *detail)) {
            throw std::runtime_error("Recast detail mesh failed");
        }
        for (int index = 0; index < poly_mesh->npolys; ++index) {
            poly_mesh->areas[index] = 0;
            poly_mesh->flags[index] = 1;
        }
        dtNavMeshCreateParams params{};
        params.verts = poly_mesh->verts;
        params.vertCount = poly_mesh->nverts;
        params.polys = poly_mesh->polys;
        params.polyAreas = poly_mesh->areas;
        params.polyFlags = poly_mesh->flags;
        params.polyCount = poly_mesh->npolys;
        params.nvp = poly_mesh->nvp;
        params.detailMeshes = detail->meshes;
        params.detailVerts = detail->verts;
        params.detailVertsCount = detail->nverts;
        params.detailTris = detail->tris;
        params.detailTriCount = detail->ntris;
        params.walkableHeight = kAgentHeight;
        params.walkableRadius = kAgentRadius;
        params.walkableClimb = kAgentClimb;
        rcVcopy(params.bmin, poly_mesh->bmin);
        rcVcopy(params.bmax, poly_mesh->bmax);
        params.cs = config.cs;
        params.ch = config.ch;
        params.buildBvTree = true;
        unsigned char* nav_data = nullptr;
        int nav_size = 0;
        if (!dtCreateNavMeshData(&params, &nav_data, &nav_size)) {
            throw std::runtime_error("Detour serialization failed");
        }
        std::unique_ptr<unsigned char, decltype(&dtFree)> owned_data(nav_data, dtFree);
        std::ofstream output(output_path, std::ios::binary | std::ios::trunc);
        if (!output.write(reinterpret_cast<const char*>(nav_data), nav_size)) {
            throw std::runtime_error("cannot write provisional Detour data");
        }
        output.close();
        std::cout << "{\"label\":\"" << label << "\",\"input_vertices\":"
                  << source_vertices.size() << ",\"selected_triangles\":" << triangle_count
                  << ",\"marked_walkable_triangles\":" << marked_walkable
                  << ",\"grid_width\":" << config.width
                  << ",\"grid_height\":" << config.height
                  << ",\"nav_vertices\":" << poly_mesh->nverts
                  << ",\"nav_polygons\":" << poly_mesh->npolys
                  << ",\"nav_bytes\":" << nav_size
                  << ",\"agent_height\":" << kAgentHeight
                  << ",\"agent_radius\":" << kAgentRadius
                  << ",\"agent_climb\":" << kAgentClimb
                  << ",\"slope_degrees\":" << kSlopeDegrees
                  << ",\"collision_verified\":false,\"navigability_verified\":false}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "bake_local_navmesh: " << error.what() << '\n';
        return 1;
    }
}
