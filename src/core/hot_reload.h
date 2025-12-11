#ifndef HOT_RELOAD_H_
#define HOT_RELOAD_H_

#include "infra/util.h"
#include <sys/stat.h>

#include <fstream>
#include <iostream>
#include <string>

#include "biodynamo.h"
#include "core/field_names.h"
#include "infra/sim_param.h"
#include "core/operation/operation.h"
#include "core/treatment_schedule.h"

namespace bdm {
namespace skibidy {

// ---------------------------------------------------------------------------
// HotReloadOp -- checks bdm.toml for modifications and re-applies parameter
// values at runtime. Enables interactive tuning without restarting the sim.
//
// Checked every metrics_interval steps (default: every 100 steps = 10h sim).
// Only numeric treatment parameters in the shared allowlist may change.
// Reload only edited keys, preserving scheduled interventions on other keys.
// ---------------------------------------------------------------------------
inline bool SameConfigNode(const toml::node& a, const toml::node& b) {
  toml::table left, right;
  left.insert("value", a);
  right.insert("value", b);
  return left == right;
}

inline toml::table RuntimeConfigDelta(const toml::table& previous,
                                      const toml::table& requested,
                                      const std::string& prefix = "") {
  toml::table delta;
  for (const auto& entry : previous) {
    if (!requested.contains(entry.first.str())) {
      throw std::invalid_argument("runtime parameter removal requires restart: " +
                                  prefix + std::string(entry.first.str()));
    }
  }
  for (const auto& entry : requested) {
    const auto key = std::string(entry.first.str());
    const auto* old = previous.get(key);
    if (old && SameConfigNode(*old, entry.second)) continue;
    const auto* nested = entry.second.as_table();
    if (nested) {
      const toml::table empty;
      const auto* old_table = old ? old->as_table() : nullptr;
      if (old && !old_table) throw std::invalid_argument("runtime table type changed: " + prefix + key);
      auto child = RuntimeConfigDelta(old_table ? *old_table : empty, *nested,
                                      prefix + key + ".");
      if (!child.empty()) delta.insert(key, std::move(child));
    } else {
      delta.insert(key, entry.second);
    }
  }
  if (prefix.empty()) ValidateTreatmentParameters(delta);
  return delta;
}

struct HotReloadOp : public StandaloneOperationImpl {
  BDM_OP_HEADER(HotReloadOp);

  HotReloadOp() = default;
  explicit HotReloadOp(const toml::table& initial) : accepted_config_(initial) {
    struct stat st;
    if (stat("bdm.toml", &st) == 0) last_mtime_ = st.st_mtime;
  }

  bool ApplyConfig(const toml::table& requested, SimParam* sp) {
    const auto delta = RuntimeConfigDelta(accepted_config_, requested);
    if (!delta.empty()) sp->LoadConfig(delta);
    accepted_config_ = requested;
    return !delta.empty();
  }

  void operator()() override {
    auto* sim = Simulation::GetActive();
    auto* sp = sim->GetParam()->Get<SimParam>();
    if (!sp->hot_reload) return;

    uint64_t step = GetGlobalStep(sim);
    int interval = sp->metrics_interval > 0 ? sp->metrics_interval : 100;
    if (step % static_cast<uint64_t>(interval) != 0) return;

    // Check file modification time
    struct stat st;
    if (stat("bdm.toml", &st) != 0) return;
    if (last_mtime_ != 0 && st.st_mtime <= last_mtime_) {
      return;
    }
    if (last_mtime_ == 0) {
      // First call: record mtime without reloading
      last_mtime_ = st.st_mtime;
      return;
    }
    last_mtime_ = st.st_mtime;

    try {
      auto config = toml::parse_file("bdm.toml");
      auto* sp_mut = const_cast<SimParam*>(sp);
      if (ApplyConfig(config, sp_mut)) RefreshTreatmentDecay(sim, sp_mut);
      std::cout << "[hot-reload] edited safe parameters accepted at step " << step
                << " (day " << step * sim->GetParam()->simulation_time_step / 24.0
                << ")" << std::endl;
    } catch (const std::exception& e) {
      std::cout << "[hot-reload] rejected without changing state: " << e.what() << std::endl;
    }
  }

 private:
  time_t last_mtime_ = 0;
  toml::table accepted_config_;
};

}  // namespace skibidy
}  // namespace bdm

#endif  // HOT_RELOAD_H_
