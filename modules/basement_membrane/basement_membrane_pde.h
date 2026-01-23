#ifndef BASEMENT_MEMBRANE_PDE_H_
#define BASEMENT_MEMBRANE_PDE_H_

#include <algorithm>
#include <cmath>
#include <vector>
#include "core/composite_field.h"
#include "core/field_names.h"
#include "core/pde.h"
#include "tissue/keratinocyte.h"

namespace bdm {
namespace skibidy {

// A two-dimensional attachment state stored in the structural grid slice
// containing z=0. Other slices are zero and never participate in repair.
struct BasementMembranePDE : public PDE {
  const char* GetName() const override { return fields::kBasementMembrane; }
  int GetId() const override { return fields::kBasementMembraneId; }

  static size_t SurfaceStart(DiffusionGrid* grid) {
    const real_t center = grid->GetDimensions()[0] + grid->GetBoxLength() / 2;
    const size_t plane = grid->GetResolution() * grid->GetResolution();
    return (grid->GetBoxIndex(Real3{center, center, 0}) / plane) * plane;
  }

  void Init(Simulation* sim) override {
    if (!sim->GetParam()->Get<SimParam>()->basement_membrane.enabled) return;
    DefineStructuralGrid(sim, 0, 0);
    auto* grid = Grid(sim);
    auto* sp = sim->GetParam()->Get<SimParam>();
    const real_t tmin = sp->tissue_min, tmax = sp->tissue_max;
    // BDM evaluates initializers after allocating the grid; use its actual
    // voxel mapping so a coarse mesh also has exactly one surface slice.
    ModelInitializer::InitializeSubstance(GetId(),
        [grid, tmin, tmax](real_t x, real_t y, real_t z) -> real_t {
          if (x < tmin || x > tmax || y < tmin || y > tmax) return 0;
          const size_t plane = grid->GetResolution() * grid->GetResolution();
          return grid->GetBoxIndex(Real3{x, y, z}) / plane ==
                     SurfaceStart(grid) / plane ? 1 : 0;
        });
    grid->SetUpperThreshold(1);
    grid->SetLowerThreshold(0);
    MarkPrescribed(sim);
  }

  void ApplyWound(Simulation* sim, real_t cx, real_t cy, real_t r) override {
    auto* sp = sim->GetParam()->Get<SimParam>();
    if (!sp->basement_membrane.enabled) return;
    auto* grid = Grid(sim);
    const GridContext ctx(grid, sp);
    const size_t start = SurfaceStart(grid), plane = ctx.res * ctx.res;
    for (size_t i = start; i < start + plane; ++i) {
      const real_t dx = ctx.X(i) - cx, dy = ctx.Y(i) - cy;
      if (dx * dx + dy * dy <= r * r) {
        grid->ChangeConcentrationBy(i,
            -sp->basement_membrane.wound_damage * grid->GetConcentration(i));
      }
    }
  }

  void ApplySource(Simulation* sim, const CompositeField& fields) override {
    auto* sp = sim->GetParam()->Get<SimParam>();
    if (!sp->basement_membrane.enabled || sp->basement_membrane.repair_rate == 0)
      return;
    auto* grid = Grid(sim);
    const GridContext ctx(grid, sp);
    const size_t plane = ctx.res * ctx.res, start = SurfaceStart(grid);
    std::vector<real_t> coverage(plane, 0);
    // Basal agents and their continuum background coexist; take the maximum
    // occupancy rather than counting the same population twice.
    sim->GetResourceManager()->ForEachAgent([&](Agent* agent) {
      auto* cell = dynamic_cast<Keratinocyte*>(agent);
      if (!cell || cell->GetStratum() != kBasal) return;
      const auto pos = cell->GetPosition();
      if (pos[2] < 0 || pos[2] > sp->volume_z_spinous ||
          pos[0] < sp->tissue_min || pos[0] > sp->tissue_max ||
          pos[1] < sp->tissue_min || pos[1] > sp->tissue_max) return;
      coverage[grid->GetBoxIndex(Real3{pos[0], pos[1], 0}) % plane] = 1;
    });
    auto* density = sp->basal_density_enabled
        ? fields.Grid(fields::kBasalDensity, sim) : nullptr;
    if (sp->basal_density_enabled && !density) {
      Log::Fatal("BasementMembranePDE::ApplySource", "BasalDensity is missing");
    }
    const real_t dt = sim->GetParam()->simulation_time_step;
    for (size_t p = 0; p < plane; ++p) {
      const size_t i = start + p;
      const Real3 pos = {ctx.X(i), ctx.Y(i), 0};
      if (pos[0] < sp->tissue_min || pos[0] > sp->tissue_max ||
          pos[1] < sp->tissue_min || pos[1] > sp->tissue_max) continue;
      if (density) {
        coverage[p] = std::max(coverage[p], std::clamp(
            density->GetConcentration(density->GetBoxIndex(pos)) /
                sp->basal_density_max, real_t(0), real_t(1)));
      }
      const real_t integrity = grid->GetConcentration(i);
      const real_t restored = (1 - integrity) *
          (-std::expm1(-sp->basement_membrane.repair_rate * coverage[p] * dt));
      if (restored > 0) grid->ChangeConcentrationBy(i, restored);
    }
  }
};

}  // namespace skibidy
}  // namespace bdm
#endif  // BASEMENT_MEMBRANE_PDE_H_
