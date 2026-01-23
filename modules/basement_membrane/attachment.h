#ifndef BASEMENT_MEMBRANE_ATTACHMENT_H_
#define BASEMENT_MEMBRANE_ATTACHMENT_H_

#include <algorithm>
#include <cmath>
#include "core/field_names.h"
#include "infra/sim_param.h"
#include "tissue/keratinocyte.h"

namespace bdm {
namespace skibidy {

// Biological attachment acts on stem cells. The z >= 0 geometric boundary
// remains a separate rule in Differentiation, even after membrane damage.
inline void ApplyBasementMembraneAnchoring(Keratinocyte* cell,
                                          Simulation* sim) {
  if (!cell->IsStem()) return;
  const auto pos = cell->GetPosition();
  const real_t max_z = cell->GetDiameter() * 0.5;
  if (pos[2] <= max_z) return;
  auto* sp = sim->GetParam()->Get<SimParam>();
  if (!sp->basement_membrane.enabled) {
    cell->SetPosition({pos[0], pos[1], max_z});
    return;
  }
  auto* grid = sim->GetResourceManager()->GetDiffusionGrid(
      fields::kBasementMembrane);
  if (!grid) Log::Fatal("ApplyBasementMembraneAnchoring",
                         "enabled BasementMembrane field is missing");
  const real_t lo = grid->GetDimensions()[0];
  const real_t hi = grid->GetDimensions()[1];
  const real_t epsilon = grid->GetBoxLength() * 1e-6;
  const Real3 surface = {std::clamp(pos[0], lo + epsilon, hi - epsilon),
                         std::clamp(pos[1], lo + epsilon, hi - epsilon), 0};
  real_t integrity = grid->GetConcentration(grid->GetBoxIndex(surface));
  if (!std::isfinite(integrity)) {
    Log::Fatal("ApplyBasementMembraneAnchoring", "nonfinite integrity");
  }
  integrity = std::clamp(integrity, real_t(0), real_t(1));
  if (integrity > 0) {
    cell->SetPosition({pos[0], pos[1],
        max_z + (pos[2] - max_z) * (1 - integrity)});
  }
}

}  // namespace skibidy
}  // namespace bdm
#endif  // BASEMENT_MEMBRANE_ATTACHMENT_H_
