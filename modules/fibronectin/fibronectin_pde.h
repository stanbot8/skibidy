#ifndef FIBRONECTIN_PDE_H_
#define FIBRONECTIN_PDE_H_

#include "core/pde.h"
#include "infra/sim_param.h"

namespace bdm {
namespace skibidy {

struct FibronectinPDE : public SimpleStructuralPDE {
  explicit FibronectinPDE(const SimParam* sp)
      : SimpleStructuralPDE(fields::kFibronectin, fields::kFibronectinId,
                            0, sp->fibronectin_decay) {}
};

}  // namespace skibidy
}  // namespace bdm

#endif  // FIBRONECTIN_PDE_H_
