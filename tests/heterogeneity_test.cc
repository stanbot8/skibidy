#include <limits>

#include "test_helpers.h"
#include "tissue/basal_division.h"

namespace bdm {
namespace skibidy {

TEST(HeterogeneityTest, FixedAndZeroWidthPreserveRandomStream) {
  auto* sim = CreateTestSim(TEST_NAME);
  auto* sp = const_cast<SimParam*>(sim->GetParam()->Get<SimParam>());
  Random control;
  for (const auto& mode : {"fixed", "normal", "lognormal"}) {
    sp->cycle_variation_distribution = mode;
    sp->cycle_variation_cv = 0;
    sim->GetRandom()->SetSeed(42);
    control.SetSeed(42);
    Keratinocyte cell({15, 15, 2});
    cell.EnsureCycleVariation(sp, sim->GetRandom());
    EXPECT_DOUBLE_EQ(cell.GetCycleDurationMultiplier(), 1);
    EXPECT_DOUBLE_EQ(sim->GetRandom()->Uniform(), control.Uniform());
  }
  delete sim;
}

TEST(HeterogeneityTest, SeedReplaysAndTraitsStayStable) {
  auto* sim = CreateTestSim(TEST_NAME);
  auto* sp = const_cast<SimParam*>(sim->GetParam()->Get<SimParam>());
  sp->cycle_variation_distribution = "lognormal";
  sp->cycle_variation_cv = 0.2;
  sim->GetRandom()->SetSeed(42);
  Keratinocyte first({15, 15, 2});
  first.EnsureCycleVariation(sp, sim->GetRandom());
  const auto value = first.GetCycleDurationMultiplier();
  const auto following = sim->GetRandom()->Uniform();
  sim->GetRandom()->SetSeed(42);
  Keratinocyte replay({15, 15, 2});
  replay.EnsureCycleVariation(sp, sim->GetRandom());
  for (int i = 0; i < 20; ++i) {
    replay.EnsureCycleVariation(sp, sim->GetRandom());
    EXPECT_DOUBLE_EQ(replay.GetCycleDurationMultiplier(), value);
  }
  EXPECT_DOUBLE_EQ(sim->GetRandom()->Uniform(), following);
  delete sim;
}

TEST(HeterogeneityTest, MultipliersHavePositiveSupportAndUnitMean) {
  auto* sim = CreateTestSim(TEST_NAME);
  auto* sp = const_cast<SimParam*>(sim->GetParam()->Get<SimParam>());
  sp->cycle_variation_cv = 0.2;
  constexpr int kSamples = 20000;
  for (const auto& mode : {"normal", "lognormal"}) {
    sp->cycle_variation_distribution = mode;
    sim->GetRandom()->SetSeed(43);
    double sum = 0, squares = 0;
    for (int i = 0; i < kSamples; ++i) {
      Keratinocyte cell({15, 15, 2});
      cell.EnsureCycleVariation(sp, sim->GetRandom());
      const auto x = cell.GetCycleDurationMultiplier();
      EXPECT_TRUE(std::isfinite(x));
      EXPECT_GT(x, 0);
      if (sp->cycle_variation_distribution == "normal") {
        EXPECT_GE(x, 0.4);
        EXPECT_LE(x, 1.6);
      }
      sum += x;
      squares += x * x;
    }
    const double mean = sum / kSamples;
    const double sd = std::sqrt(squares / kSamples - mean * mean);
    EXPECT_NEAR(mean, 1, 0.01);
    EXPECT_NEAR(sd, 0.2, 0.01);
  }
  delete sim;
}

TEST(HeterogeneityTest, DaughterSamplesOwnTraitAndMotherRetainsHers) {
  auto* sim = CreateTestSim(TEST_NAME);
  auto* sp = const_cast<SimParam*>(sim->GetParam()->Get<SimParam>());
  sp->cycle_variation_distribution = "normal";
  sp->cycle_variation_cv = 0.2;
  auto* mother = new Keratinocyte({15, 15, 2});
  mother->SetDiameter(8);
  mother->EnsureCycleVariation(sp, sim->GetRandom());
  const auto original = mother->GetCycleDurationMultiplier();
  sim->GetResourceManager()->AddAgent(mother);
  auto* daughter = dynamic_cast<Keratinocyte*>(mother->Divide());
  ASSERT_NE(daughter, nullptr);
  EXPECT_DOUBLE_EQ(mother->GetCycleDurationMultiplier(), original);
  EXPECT_NE(daughter->GetCycleDurationMultiplier(), original);
  const auto daughter_value = daughter->GetCycleDurationMultiplier();
  daughter->EnsureCycleVariation(sp, sim->GetRandom());
  EXPECT_DOUBLE_EQ(daughter->GetCycleDurationMultiplier(), daughter_value);
  delete sim;
}

TEST(HeterogeneityTest, SPhaseUsesPersistentDuration) {
  auto* sim = CreateTestSim(TEST_NAME);
  auto* sp = const_cast<SimParam*>(sim->GetParam()->Get<SimParam>());
  sp->cycle_variation_distribution = "lognormal";
  sp->cycle_variation_cv = 0.2;
  sp->homeostasis_subcycle = 1;
  sp->wound.enabled = false;
  Keratinocyte cell({15, 15, 2});
  cell.SetDiameter(5);
  cell.EnsureCycleVariation(sp, sim->GetRandom());
  Random control;
  control.SetSeed(44);
  const auto ran = control.Uniform();
  const auto effective_duration = sp->s_duration *
                                 cell.GetCycleDurationMultiplier();
  BasalDivision behavior;
  for (const auto delta : {-0.001, 0.001}) {
    cell.SetCyclePhase(kS);
    cell.SetPhaseElapsed((ran + delta) * effective_duration -
                         sim->GetParam()->simulation_time_step);
    sim->GetRandom()->SetSeed(44);
    behavior.Run(&cell);
    EXPECT_EQ(cell.GetCyclePhase(), delta < 0 ? kS : kG2);
  }
  delete sim;
}

TEST(HeterogeneityTest, ConfigRejectsInvalidSpreadAndMode) {
  SimParam sp;
  sp.LoadConfig(toml::parse("[skin.heterogeneity]\n"
                          "cycle_distribution = 'lognormal'\ncycle_cv = 0.2"));
  EXPECT_EQ(sp.cycle_variation_distribution, "lognormal");
  EXPECT_DOUBLE_EQ(sp.cycle_variation_cv, 0.2);
  sp.ValidateConfig();
  for (const auto invalid : {-0.1, 1.1,
       std::numeric_limits<double>::infinity(),
       std::numeric_limits<double>::quiet_NaN()}) {
    sp.cycle_variation_cv = invalid;
    EXPECT_DEATH(sp.ValidateConfig(), "heterogeneity.cycle_cv");
  }
  sp.cycle_variation_cv = 0.4;
  sp.cycle_variation_distribution = "normal";
  EXPECT_DEATH(sp.ValidateConfig(), "normal heterogeneity");
  sp.cycle_variation_distribution = "fixed";
  EXPECT_DEATH(sp.ValidateConfig(), "fixed heterogeneity");
  sp.cycle_variation_distribution = "unknown";
  EXPECT_DEATH(sp.ValidateConfig(), "cycle_distribution");
  EXPECT_DEATH(sp.LoadConfig(toml::parse(
      "[skin.heterogeneity]\ncycle_cv = 'wide'")), "must be a number");
}

}  // namespace skibidy
}  // namespace bdm
