#include "test_helpers.h"
#include "basement_membrane/attachment.h"
#include "basement_membrane/basement_membrane_pde.h"
#include "tissue/differentiation.h"
#include <limits>

namespace bdm {
namespace skibidy {

static DiffusionGrid* InitMembraneTest(Simulation* sim, BasementMembranePDE* pde) {
  auto* sp = const_cast<SimParam*>(sim->GetParam()->Get<SimParam>());
  SanitizeForUnitTest(sp);
  sp->basement_membrane.enabled = true;
  sp->basal_density_enabled = false;
  sp->wound.enabled = false;
  pde->Init(sim);
  sim->GetEnvironment()->Update();
  auto* grid = pde->Grid(sim);
  grid->Initialize();
  grid->RunInitializers();
  return grid;
}

TEST(BasementMembraneTest, DisabledAnchoringPreservesHeightAndRandomStream) {
  auto* sim = CreateTestSim(TEST_NAME);
  auto* sp = const_cast<SimParam*>(sim->GetParam()->Get<SimParam>());
  sp->basement_membrane.enabled = false;
  Random control;
  control.SetSeed(924);
  sim->GetRandom()->SetSeed(924);
  Keratinocyte cell({25, 25, 10});
  cell.SetDiameter(4);
  cell.SetDivisionsLeft(-1);
  ApplyBasementMembraneAnchoring(&cell, sim);
  EXPECT_DOUBLE_EQ(cell.GetPosition()[2], 2);
  EXPECT_DOUBLE_EQ(sim->GetRandom()->Uniform(), control.Uniform());
  BasementMembranePDE membrane;
  membrane.Init(sim);
  EXPECT_EQ(sim->GetResourceManager()->GetDiffusionGrid(
                fields::kBasementMembraneId), nullptr);
  delete sim;
}

TEST(BasementMembraneTest, SingleSurfaceSliceAndSuppliedWoundGeometry) {
  auto* sim = CreateTestSim(TEST_NAME);
  auto* sp = const_cast<SimParam*>(sim->GetParam()->Get<SimParam>());
  sp->grid_resolution_structural = 5;
  BasementMembranePDE membrane;
  auto* grid = InitMembraneTest(sim, &membrane);
  const GridContext ctx(grid, sp);
  const size_t start = BasementMembranePDE::SurfaceStart(grid);
  const size_t plane = ctx.res * ctx.res;
  const size_t target = start + 2 * ctx.res + 2;
  ASSERT_DOUBLE_EQ(grid->GetConcentration(target), 1);
  for (size_t i = start + plane; i < grid->GetNumBoxes(); ++i)
    EXPECT_DOUBLE_EQ(grid->GetConcentration(i), 0);
  sp->wound.center_x = -100;
  sp->wound.center_y = -100;
  sp->basement_membrane.wound_damage = 0.4;
  membrane.ApplyWound(sim, ctx.X(target), ctx.Y(target), 0.01);
  EXPECT_NEAR(grid->GetConcentration(target), 0.6, 1e-12);
  EXPECT_DOUBLE_EQ(grid->GetConcentration(target + 1), 1);
  delete sim;
}

TEST(BasementMembraneTest, RepairRequiresBasalCoverageAndRestoresAttachment) {
  auto* sim = CreateTestSim(TEST_NAME);
  auto* sp = const_cast<SimParam*>(sim->GetParam()->Get<SimParam>());
  BasementMembranePDE membrane;
  auto* grid = InitMembraneTest(sim, &membrane);
  const size_t idx = grid->GetBoxIndex(Real3{25, 25, 0});
  grid->ChangeConcentrationBy(idx, -1);
  CompositeField composite;
  membrane.ApplySource(sim, composite);
  EXPECT_DOUBLE_EQ(grid->GetConcentration(idx), 0);
  auto* basal = new Keratinocyte({25, 25, 1});
  basal->SetStratum(kBasal);
  sim->GetResourceManager()->AddAgent(basal);
  sp->basement_membrane.repair_rate = 2;
  membrane.ApplySource(sim, composite);
  const real_t repaired = -std::expm1(-2 * sim->GetParam()->simulation_time_step);
  EXPECT_NEAR(grid->GetConcentration(idx), repaired, 1e-12);
  Keratinocyte displaced({25, 25, 10});
  displaced.SetDiameter(4);
  displaced.SetDivisionsLeft(-1);
  ApplyBasementMembraneAnchoring(&displaced, sim);
  EXPECT_NEAR(displaced.GetPosition()[2], 2 + 8 * (1 - repaired), 1e-12);
  sp->basement_membrane.repair_rate = 1e6;
  membrane.ApplySource(sim, composite);
  EXPECT_DOUBLE_EQ(grid->GetConcentration(idx), 1);
  delete sim;
}

TEST(BasementMembraneTest, ContinuumCoverageMapsAcrossGridResolutions) {
  auto* sim = CreateTestSim(TEST_NAME);
  auto* sp = const_cast<SimParam*>(sim->GetParam()->Get<SimParam>());
  sp->grid_resolution_structural = 5;
  BasementMembranePDE membrane;
  auto* grid = InitMembraneTest(sim, &membrane);
  CompositeField composite;
  composite.Add(std::make_unique<SimplePDE>(fields::kBasalDensity,
      fields::kBasalDensityId, 0, 0));
  composite.InitAll(sim);
  auto* density = composite.Grid(fields::kBasalDensity, sim);
  density->Initialize();
  sp->basal_density_enabled = true;
  const GridContext ctx(grid, sp);
  const size_t idx = grid->GetBoxIndex(Real3{25, 25, 0});
  const Real3 pos = {ctx.X(idx), ctx.Y(idx), 0};
  density->ChangeConcentrationBy(density->GetBoxIndex(pos),
                                sp->basal_density_max * 0.5);
  grid->ChangeConcentrationBy(idx, -1);
  membrane.ApplySource(sim, composite);
  EXPECT_NEAR(grid->GetConcentration(idx), -std::expm1(
      -sp->basement_membrane.repair_rate * 0.5 *
       sim->GetParam()->simulation_time_step), 1e-12);
  delete sim;
}

TEST(BasementMembraneTest, DifferentiationConsumesDamageButRetainsGeometricFloor) {
  auto* sim = CreateTestSim(TEST_NAME);
  auto* sp = const_cast<SimParam*>(sim->GetParam()->Get<SimParam>());
  BasementMembranePDE membrane;
  auto* grid = InitMembraneTest(sim, &membrane);
  SimplePDE calcium(fields::kCalcium, fields::kCalciumId, 0, 0);
  calcium.Init(sim);
  auto* ca = calcium.Grid(sim);
  ca->Initialize();
  VolumeManager::Get()->Init(sp->volume_z_spinous, sp->volume_z_granular,
                            sp->volume_z_cornified);
  g_voxel_env.Fill(sim);
  Differentiation diff;
  Keratinocyte cell({25, 25, 10});
  cell.SetDiameter(4);
  cell.SetDivisionsLeft(-1);
  diff.Run(&cell);
  EXPECT_DOUBLE_EQ(cell.GetPosition()[2], 2);
  const size_t idx = grid->GetBoxIndex(Real3{25, 25, 0});
  grid->ChangeConcentrationBy(idx, -0.5);
  cell.SetPosition({25, 25, 10});
  diff.Run(&cell);
  EXPECT_DOUBLE_EQ(cell.GetPosition()[2], 6);
  grid->ChangeConcentrationBy(idx, -0.5);
  cell.SetPosition({25, 25, 10});
  diff.Run(&cell);
  EXPECT_DOUBLE_EQ(cell.GetPosition()[2], 10);
  cell.SetPosition({25, 25, -1});
  diff.Run(&cell);
  EXPECT_DOUBLE_EQ(cell.GetPosition()[2], 0);
  delete sim;
}

TEST(BasementMembraneTest, ConfigRejectsInvalidTypesAndRates) {
  SimParam sp;
  sp.LoadConfig(toml::parse("[skin.basement_membrane]\nenabled=true\n"
                           "wound_damage=0.5\nrepair_rate=0.0"));
  EXPECT_TRUE(sp.basement_membrane.enabled);
  EXPECT_DOUBLE_EQ(sp.basement_membrane.wound_damage, 0.5);
  EXPECT_DOUBLE_EQ(sp.basement_membrane.repair_rate, 0);
  sp.ValidateConfig();
  sp.basal_density_enabled = true;
  sp.basal_density_max = 0;
  EXPECT_DEATH(sp.ValidateConfig(), "positive basal_density_max");
  sp.basal_density_max = 1;
  EXPECT_DEATH(sp.LoadConfig(toml::parse(
      "[skin.basement_membrane]\nenabled='yes'")), "must be a boolean");
  EXPECT_DEATH(sp.LoadConfig(toml::parse(
      "[skin.basement_membrane]\nrepair_rate='fast'")), "must be a number");
  for (real_t value : {-0.1, 1.1, std::numeric_limits<real_t>::infinity(),
                       std::numeric_limits<real_t>::quiet_NaN()}) {
    sp.basement_membrane.wound_damage = value;
    EXPECT_DEATH(sp.ValidateConfig(), "wound_damage");
  }
  sp.basement_membrane.wound_damage = 1;
  for (real_t value : {-0.1, std::numeric_limits<real_t>::infinity(),
                       std::numeric_limits<real_t>::quiet_NaN()}) {
    sp.basement_membrane.repair_rate = value;
    EXPECT_DEATH(sp.ValidateConfig(), "repair_rate");
  }
}

}  // namespace skibidy
}  // namespace bdm
