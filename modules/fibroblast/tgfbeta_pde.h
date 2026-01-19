#ifndef TGFBETA_PDE_H_
#define TGFBETA_PDE_H_

#include "core/pde.h"
#include "infra/sim_param.h"

namespace bdm {
namespace skibidy {

struct TGFBetaPDE : public SimplePDE {
  explicit TGFBetaPDE(const SimParam* sp)
      : SimplePDE(fields::kTGFBeta, fields::kTGFBetaId,
                  sp->tgfb_diffusion, sp->tgfb_decay) {}
};

}  // namespace skibidy
}  // namespace bdm

#endif  // TGFBETA_PDE_H_
