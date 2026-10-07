#ifndef BASEMENT_MEMBRANE_PARAMS_H_
#define BASEMENT_MEMBRANE_PARAMS_H_

#include "biodynamo.h"

namespace bdm {
namespace skibidy {

struct BasementMembraneParams {
  bool enabled = false;
  // Research assumptions, not measured human wound coefficients.
  real_t wound_damage = 1.0;    // fraction removed by each wound event
  real_t repair_rate = 0.005;  // per hour at full local basal coverage
};

}  // namespace skibidy
}  // namespace bdm
#endif  // BASEMENT_MEMBRANE_PARAMS_H_
