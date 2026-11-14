// Offline source-only span attribution, not a navmesh or movement permit.
// Compile against the hash-pinned retained Recast tree/library. Including
// this translation unit lets us inspect its actual static getCornerHeight
// without editing upstream source or guessing its neighbor-height behavior.
#include "RecastContour.cpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <set>
#include <sstream>
#include <stdexcept>
#include <vector>

namespace {
struct Node { float plane[4]; std::int32_t pos, neg; };
struct Probe { const char* name; float x, z; int cell_x, cell_z; };
using Cells = std::set<std::pair<int, int>>;

template <typename T> void read(std::ifstream& in, T* out, std::size_t count) {
    if (!in.read(reinterpret_cast<char*>(out), sizeof(T) * count))
        throw std::runtime_error("truncated EQTR");
}

std::string raw_cells(const rcHeightfield& hf, const Cells& cells) {
    std::ostringstream out;
    out << std::setprecision(10) << '[';
    bool first = true;
    for (auto [x, z] : cells) {
        if (!first) out << ',';
        first = false;
        out << "{\"x\":" << x << ",\"z\":" << z << ",\"spans\":[";
        bool first_span = true;
        for (auto* span = hf.spans[x + z * hf.width]; span; span = span->next) {
            if (!first_span) out << ',';
            first_span = false;
            out << "{\"smin\":" << span->smin << ",\"smax\":" << span->smax
                << ",\"area\":" << span->area << ",\"world_top\":"
                << hf.bmin[1] + span->smax * hf.ch << '}';
        }
        out << "]}";
    }
    return out.str() + ']';
}

bool near_probes(const float* a, const float* b, const float* c,
                 const std::vector<Probe>& probes, float margin) {
    for (const auto& p : probes) {
        if (std::max({a[0], b[0], c[0]}) >= p.x - margin &&
            std::min({a[0], b[0], c[0]}) <= p.x + margin &&
            std::max({a[2], b[2], c[2]}) >= p.z - margin &&
            std::min({a[2], b[2], c[2]}) <= p.z + margin) return true;
    }
    return false;
}

int classify(const std::vector<Node>& nodes, float x, float y, float z) {
    int index = 0;
    for (std::size_t depth = 0; depth <= nodes.size(); ++depth) {
        if (index < 0) {
            const int area = -(index + 1);
            if (area < 0 || area > 63) throw std::runtime_error("invalid BSP area");
            return area;
        }
        if (index >= static_cast<int>(nodes.size())) throw std::runtime_error("invalid BSP link");
        const auto& n = nodes[index];
        index = n.plane[0]*x + n.plane[1]*y + n.plane[2]*z + n.plane[3] >= 0 ? n.pos : n.neg;
    }
    throw std::runtime_error("BSP cycle");
}
}

int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::runtime_error("usage: probe_crushbone_spans INPUT.eqtr");
        std::ifstream input(argv[1], std::ios::binary);
        char magic[4]; std::uint32_t header[4];
        read(input, magic, 4); read(input, header, 4);
        if (std::string(magic, 4) != "EQTR" || header[0] != 1 ||
            header[1] != 79710 || header[2] != 26570 || header[3] != 5586)
            throw std::runtime_error("unexpected pinned Crushbone inventory");
        static_assert(sizeof(Node) == 24 && sizeof(float) == 4 && sizeof(int) == 4);
        std::vector<float> verts(header[1] * 3);
        std::vector<int> tris(header[2] * 3);
        std::vector<Node> nodes(header[3]);
        read(input, verts.data(), verts.size()); read(input, tris.data(), tris.size());
        read(input, nodes.data(), nodes.size());
        if (input.peek() != std::char_traits<char>::eof()) throw std::runtime_error("trailing EQTR bytes");
        for (float v : verts) if (!std::isfinite(v)) throw std::runtime_error("invalid vertex");
        for (int i : tris) if (i < 0 || i >= int(header[1])) throw std::runtime_error("invalid triangle");

        float global_min[3], global_max[3];
        rcCalcBounds(verts.data(), header[1], global_min, global_max);
        rcConfig cfg{};
        cfg.cs = .6f; cfg.ch = .3f; cfg.tileSize = 256;
        cfg.walkableHeight = int(std::ceil(6.f / cfg.ch));
        cfg.walkableClimb = int(std::floor(3.5f / cfg.ch));
        cfg.walkableRadius = int(std::ceil(1.2f / cfg.cs));
        cfg.walkableSlopeAngle = 75;
        cfg.borderSize = cfg.walkableRadius + 3;
        cfg.width = cfg.height = cfg.tileSize + 2 * cfg.borderSize;
        rcVcopy(cfg.bmin, global_min); rcVcopy(cfg.bmax, global_max);
        cfg.bmin[0] += 6 * cfg.tileSize * cfg.cs - cfg.borderSize * cfg.cs;
        cfg.bmin[2] += cfg.tileSize * cfg.cs - cfg.borderSize * cfg.cs;
        cfg.bmax[0] = cfg.bmin[0] + cfg.width * cfg.cs;
        cfg.bmax[2] = cfg.bmin[2] + cfg.height * cfg.cs;
        std::vector<Probe> probes = {
            {"west_high", 99.94378662109375f, -186.44374084472656f, 0, 0},
            {"east_high", 98.74378967285156f, -172.64373779296875f, 0, 0},
            {"cut_center", 98.74378967285156f, -180.14373779296875f, 0, 0},
        };
        Cells cells;
        for (auto& p : probes) {
            p.cell_x = int(std::lround((p.x - cfg.bmin[0]) / cfg.cs));
            p.cell_z = int(std::lround((p.z - cfg.bmin[2]) / cfg.cs));
            for (int z = p.cell_z - 1; z <= p.cell_z; ++z)
                for (int x = p.cell_x - 1; x <= p.cell_x; ++x) {
                    if (x < 1 || z < 1 || x >= cfg.width-1 || z >= cfg.height-1)
                        throw std::runtime_error("probe outside bounded tile");
                    cells.insert({x,z});
                }
        }
        rcContext context(false);
        std::unique_ptr<rcHeightfield, decltype(&rcFreeHeightField)> hf(rcAllocHeightfield(), rcFreeHeightField);
        if (!hf || !rcCreateHeightfield(&context, *hf, cfg.width, cfg.height, cfg.bmin, cfg.bmax, cfg.cs, cfg.ch))
            throw std::runtime_error("heightfield allocation failed");
        std::vector<unsigned char> areas(header[2], 0);
        rcMarkWalkableTriangles(&context, cfg.walkableSlopeAngle, verts.data(), header[1], tris.data(), header[2], areas.data());
        std::cout << std::setprecision(10)
                  << "{\"format\":\"eql-source-span-probe-v1\",\"exact_custom_baker_equivalence\":false,"
                  << "\"game_input_sent\":false,\"route_accepted\":false,\"tile\":[6,1],"
                  << "\"config\":{\"width\":" << cfg.width << ",\"height\":" << cfg.height
                  << ",\"cs\":" << cfg.cs << ",\"ch\":" << cfg.ch << ",\"border\":" << cfg.borderSize
                  << ",\"walkable_height\":" << cfg.walkableHeight << ",\"walkable_climb\":" << cfg.walkableClimb
                  << ",\"walkable_radius\":" << cfg.walkableRadius << ",\"bmin\":["
                  << cfg.bmin[0] << ',' << cfg.bmin[1] << ',' << cfg.bmin[2] << "],\"bmax\":["
                  << cfg.bmax[0] << ',' << cfg.bmax[1] << ',' << cfg.bmax[2] << "]},\"probes\":[";
        bool first = true;
        for (const auto& p : probes) {
            if (!first) std::cout << ',';
            first = false;
            std::cout << "{\"name\":\"" << p.name << "\",\"recast_xz\":[" << p.x << ',' << p.z
                      << "],\"rounded_cell\":[" << p.cell_x << ',' << p.cell_z
                      << "],\"bsp_area_at_y2\":" << classify(nodes, p.x, 2.f, p.z) << '}';
        }
        std::cout << "],\"raw_contributors\":[";
        first = true;
        for (unsigned int i = 0; i < header[2]; ++i) {
            const float* a = &verts[tris[3*i]*3];
            const float* b = &verts[tris[3*i+1]*3];
            const float* c = &verts[tris[3*i+2]*3];
            const bool observe = near_probes(a,b,c,probes,1.3f);
            const auto before = observe ? raw_cells(*hf, cells) : std::string();
            if (!rcRasterizeTriangle(&context,a,b,c,areas[i],*hf,cfg.walkableClimb))
                throw std::runtime_error("rasterization failed");
            if (observe) {
                const auto after = raw_cells(*hf,cells);
                if (before != after) {
                    if (!first) std::cout << ',';
                    first = false;
                    std::cout << "{\"source_triangle\":" << i << ",\"slope_area\":" << int(areas[i])
                              << ",\"after\":" << after << '}';
                }
            }
        }
        std::cout << "],\"stages\":{\"raw\":" << raw_cells(*hf,cells);
        rcFilterLowHangingWalkableObstacles(&context,cfg.walkableClimb,*hf);
        std::cout << ",\"after_low_hanging\":" << raw_cells(*hf,cells);
        rcFilterLedgeSpans(&context,cfg.walkableHeight,cfg.walkableClimb,*hf);
        std::cout << ",\"after_ledges\":" << raw_cells(*hf,cells);
        rcFilterWalkableLowHeightSpans(&context,cfg.walkableHeight,*hf);
        std::cout << ",\"after_clearance\":" << raw_cells(*hf,cells) << "},\"compact\":[";
        std::unique_ptr<rcCompactHeightfield, decltype(&rcFreeCompactHeightfield)> chf(rcAllocCompactHeightfield(),rcFreeCompactHeightfield);
        if (!chf || !rcBuildCompactHeightfield(&context,cfg.walkableHeight,cfg.walkableClimb,*hf,*chf))
            throw std::runtime_error("compact build failed");
        first = true;
        for (auto [x,z] : cells) {
            const auto& cell = chf->cells[x+z*chf->width];
            const unsigned int end = cell.index + cell.count;
            for (unsigned int i=cell.index; i<end; ++i) {
                if (!first) std::cout << ',';
                first = false;
                const auto& span = chf->spans[i];
                std::cout << "{\"x\":" << x << ",\"z\":" << z << ",\"index\":" << i
                          << ",\"y\":" << span.y << ",\"h\":" << span.h << ",\"area\":" << int(chf->areas[i])
                          << ",\"world_y\":" << chf->bmin[1]+span.y*chf->ch << ",\"neighbors\":[";
                for (int dir=0; dir<4; ++dir) {
                    if (dir) std::cout << ',';
                    const int con = rcGetCon(span,dir);
                    if (con == RC_NOT_CONNECTED) { std::cout << "null"; continue; }
                    const int ax=x+rcGetDirOffsetX(dir), az=z+rcGetDirOffsetY(dir);
                    const int ni=chf->cells[ax+az*chf->width].index+con;
                    std::cout << "{\"x\":" << ax << ",\"z\":" << az << ",\"index\":" << ni
                              << ",\"y\":" << chf->spans[ni].y << '}';
                }
                std::cout << "],\"corner_y_by_direction\":[";
                for (int dir=0;dir<4;++dir) {
                    if (dir) std::cout << ',';
                    bool border=false;
                    std::cout << getCornerHeight(x,z,i,dir,*chf,border);
                }
                std::cout << "]}";
            }
        }
        std::cout << "],\"regions_built\":false,\"bsp_applied_to_spans\":false}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "Source span probe refused: " << error.what() << '\n';
        return 1;
    }
}
