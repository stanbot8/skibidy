#include "test_helpers.h"
#include "core/treatment_schedule.h"
#include "core/hot_reload.h"

namespace bdm {
namespace skibidy {

TEST(TreatmentTiming, StartsAtBoundaryAndOnlyOnce) {
  SimParam sp;
  const auto original = sp.water_recovery_rate;
  TreatmentSchedule schedule(toml::parse(R"(
[[treatment_schedule]]
start_day = 7
parameters = "[skin]\nwater_recovery_rate = 0.06\n"
)"), 0.1);
  EXPECT_FALSE(schedule.Apply(1679, &sp));
  EXPECT_EQ(sp.water_recovery_rate, original);
  EXPECT_TRUE(schedule.Apply(1680, &sp));
  EXPECT_DOUBLE_EQ(sp.water_recovery_rate, 0.06);
  sp.water_recovery_rate = 0.02;
  EXPECT_FALSE(schedule.Apply(1681, &sp));
  EXPECT_DOUBLE_EQ(sp.water_recovery_rate, 0.02);
}

TEST(TreatmentTiming, StableChronologicalCombinationOrder) {
  SimParam sp;
  TreatmentSchedule schedule(toml::parse(R"(
[[treatment_schedule]]
start_day = 2
parameters = "[skin]\nwater_recovery_rate = 0.08\n"
[[treatment_schedule]]
start_day = 0
parameters = "[skin]\nwater_recovery_rate = 0.04\n"
[[treatment_schedule]]
start_day = 2
parameters = "[skin]\nwater_recovery_rate = 0.06\n"
)"), 0.1);
  EXPECT_TRUE(schedule.Apply(0, &sp));
  EXPECT_DOUBLE_EQ(sp.water_recovery_rate, 0.04);
  EXPECT_TRUE(schedule.Apply(480, &sp));
  EXPECT_DOUBLE_EQ(sp.water_recovery_rate, 0.06);
}

TEST(TreatmentTiming, RejectsTopologyAndInvalidRatesBeforeMutation) {
  EXPECT_THROW(ValidateTreatmentParameters(toml::parse(
      "[skin.mmp]\nenabled = false\n")), std::invalid_argument);
  EXPECT_THROW(ValidateTreatmentParameters(toml::parse(
      "[geometry]\npatch_um = 500\n")), std::invalid_argument);
  EXPECT_THROW(ValidateTreatmentParameters(toml::parse(
      "[skin]\nwater_recovery_rate = nan\n")), std::invalid_argument);
  EXPECT_THROW(ValidateTreatmentParameters(toml::parse(
      "[skin.wound]\ninward_bias = 2\n")), std::invalid_argument);
}

TEST(TreatmentTiming, RefreshesAllInflammationGridOwners) {
  auto* sim = CreateTestSim(TEST_NAME);
  auto* sp = const_cast<SimParam*>(sim->GetParam()->Get<SimParam>());
  CompositeField field;
  field.Add(std::make_unique<InflammationPDE>(sp));
  field.Add(std::make_unique<ImmunePressurePDE>(sp));
  field.InitAll(sim);
  sp->inflammation.decay = 0.004;
  RefreshTreatmentDecay(sim, sp);
  for (int id : {fields::kInflammationId, fields::kImmunePressureId}) {
    EXPECT_DOUBLE_EQ(sim->GetResourceManager()->GetDiffusionGrid(id)->GetDecayConstant(), 0.004);
  }
  delete sim;
}

TEST(TreatmentTiming, HotReloadPreservesScheduledValuesAndRejectsUnsafeDeltaAtomically) {
  auto initial = toml::parse("[skin]\nwater_recovery_rate = 0.02\nwater_surface_loss_rate = 0.03\n[geometry]\npatch_um = 500\n");
  HotReloadOp reload(initial);
  SimParam sp;
  sp.water_recovery_rate = 0.06;  // an already applied scheduled intervention
  EXPECT_FALSE(reload.ApplyConfig(initial, &sp));
  EXPECT_DOUBLE_EQ(sp.water_recovery_rate, 0.06);
  auto requested = initial;
  requested["skin"].as_table()->insert_or_assign("water_surface_loss_rate", 0.005);
  EXPECT_TRUE(reload.ApplyConfig(requested, &sp));
  EXPECT_DOUBLE_EQ(sp.water_recovery_rate, 0.06);
  EXPECT_DOUBLE_EQ(sp.water_surface_loss_rate, 0.005);
  requested["skin"].as_table()->insert_or_assign("water_recovery_rate", 0.08);
  requested["geometry"].as_table()->insert_or_assign("patch_um", 900);
  EXPECT_THROW(reload.ApplyConfig(requested, &sp), std::invalid_argument);
  EXPECT_DOUBLE_EQ(sp.water_recovery_rate, 0.06);
}
}  // namespace skibidy
}  // namespace bdm
