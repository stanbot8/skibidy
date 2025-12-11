#ifndef SKIBIDY_TREATMENT_SCHEDULE_H_
#define SKIBIDY_TREATMENT_SCHEDULE_H_

#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <unordered_set>
#include <vector>

#include "biodynamo.h"
#include "core/field_names.h"
#include "infra/sim_param.h"
#include "infra/toml_compat.h"
#include "infra/util.h"

namespace bdm {
namespace skibidy {

inline bool IsRuntimeTreatmentKey(const std::string& key) {
  static const std::unordered_set<std::string> keys = {
#define SKIBIDY_RUNTIME_PARAMETER(path) path,
#include "core/runtime_treatment_keys.inc"
#undef SKIBIDY_RUNTIME_PARAMETER
  };
  return keys.count(key) != 0;
}

inline void ValidateTreatmentParameters(const toml::table& table,
                                       const std::string& prefix = "") {
  for (const auto& entry : table) {
    const auto key = prefix + std::string(entry.first.str());
    if (const auto* nested = entry.second.as_table()) {
      ValidateTreatmentParameters(*nested, key + ".");
      continue;
    }
    auto value = entry.second.value<double>();
    if (!IsRuntimeTreatmentKey(key) || !value ||
        !std::isfinite(*value) || *value < 0 ||
        (key == "skin.wound.inward_bias" && *value > 1)) {
      throw std::invalid_argument("unsafe or invalid scheduled parameter: " + key);
    }
  }
}

// These coefficients live in diffusion grids rather than being read from
// SimParam by each source hook. Keep all coupled inflammation grids consistent.
inline void RefreshTreatmentDecay(Simulation* sim, const SimParam* sp) {
  auto set = [&](int id, real_t decay) {
    if (auto* grid = sim->GetResourceManager()->GetDiffusionGrid(id)) {
      grid->SetDecayConstant(decay);
    }
  };
  set(sp->inflammation.split_inflammation_enabled ? fields::kProInflammatoryId
                                                 : fields::kInflammationId,
      sp->inflammation.decay);
  set(fields::kImmunePressureId, sp->inflammation.decay);
  if (sp->mmp.enabled) {
    set(fields::kMMPId, sp->mmp.residual_decay);
    set(fields::kTIMPId, sp->mmp.timp_decay);
  }
}

struct TreatmentEvent {
  uint64_t start_step;
  std::string name;
  toml::table parameters;
};

// Absolute start days, measured from simulation time zero. Stable sorting makes
// overlapping treatments explicit: chronological order, then declared order;
// the last treatment to write a parameter wins. Events persist until overwritten.
class TreatmentSchedule {
 public:
  TreatmentSchedule() = default;
  TreatmentSchedule(const toml::table& config, double dt_hours) {
    if (!std::isfinite(dt_hours) || dt_hours <= 0) {
      throw std::invalid_argument("invalid treatment schedule timestep");
    }
    const auto node = config["treatment_schedule"];
    if (!node) return;
    const auto* schedule = node.as_array();
    if (!schedule) throw std::invalid_argument("treatment_schedule must be an array");
    for (const auto& item : *schedule) {
      const auto* table = item.as_table();
      if (!table) throw std::invalid_argument("treatment event must be a table");
      for (const auto& entry : *table) {
        const auto key = entry.first.str();
        if (key != "name" && key != "start_day" && key != "parameters") {
          throw std::invalid_argument("unknown treatment event key: " + std::string(key));
        }
      }
      const auto start = (*table)["start_day"].value<double>();
      const auto text = (*table)["parameters"].value<std::string>();
      const double steps = start ? *start * 24.0 / dt_hours : -1;
      if (!start || !std::isfinite(steps) || steps < 0 ||
          steps >= static_cast<double>(std::numeric_limits<uint64_t>::max()) || !text) {
        throw std::invalid_argument("invalid treatment start_day or parameters");
      }
      auto parameters = toml::parse(*text);
      if (parameters.empty()) throw std::invalid_argument("empty treatment parameters");
      ValidateTreatmentParameters(parameters);
      events_.push_back({static_cast<uint64_t>(std::ceil(steps - 1e-9)),
                         (*table)["name"].value_or(std::string("treatment")),
                         std::move(parameters)});
    }
    std::stable_sort(events_.begin(), events_.end(),
                     [](const TreatmentEvent& a, const TreatmentEvent& b) {
                       return a.start_step < b.start_step;
                     });
  }

  bool Apply(uint64_t step, SimParam* sp) {
    bool changed = false;
    while (next_ < events_.size() && events_[next_].start_step <= step) {
      const auto& event = events_[next_++];
      sp->LoadConfig(event.parameters);
      std::cout << "[treatment] " << event.name << " applied at step " << step
                << " (scheduled step " << event.start_step << ")" << std::endl;
      changed = true;
    }
    return changed;
  }
  size_t NextEvent() const { return next_; }
  const std::vector<TreatmentEvent>& Events() const { return events_; }

 private:
  std::vector<TreatmentEvent> events_;
  size_t next_ = 0;
};

struct TreatmentScheduleOp : public StandaloneOperationImpl {
  BDM_OP_HEADER(TreatmentScheduleOp);
  TreatmentScheduleOp() = default;
  explicit TreatmentScheduleOp(const toml::table& config, double dt)
      : schedule_(config, dt) {}
  void operator()() override {
    auto* sim = Simulation::GetActive();
    auto* sp = const_cast<SimParam*>(sim->GetParam()->Get<SimParam>());
    if (schedule_.Apply(GetGlobalStep(sim), sp)) RefreshTreatmentDecay(sim, sp);
  }
 private:
  TreatmentSchedule schedule_;
};

}  // namespace skibidy
}  // namespace bdm
#endif
