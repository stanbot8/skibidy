> [Home](../README.md) / [Docs](README.md) / Wound Healing

# Wound Healing

Circular punch biopsy wound with immune response, re-epithelialization, fibroblast/collagen cascade, and emergent scar formation. Enable with `[skin.wound] enabled = true` or `--preset=wound`. See also: [Guide](guide.md) | [Parameters](parameters.md) | [Architecture](architecture.md)

For detailed module documentation including parameters, coupling, and validation, see the per-module READMEs linked below.

## Wound event pipeline

1. **WoundEvent** zeros Stratum/Calcium/O2 fields in the wound cylinder and spawns basal keratinocytes at the margin. See [wound module](../modules/wound/README.md).
2. **ImmuneResponse** spawns neutrophils (~2h post-wound) and macrophages (~12h) at the wound margin. See [immune module](../modules/immune/README.md).
3. **Field-driven initialization**: spawned agents read local Calcium, KGF, and O2 to derive stem identity, TA division budget, and cell cycle readiness. See [tissue module](../modules/tissue/README.md).
4. **Active cell migration**: basal keratinocytes crawl toward wound center via tractor force, gated by immune pressure, water, and fibronectin.
5. **Inward division bias** (`wound_inward_bias`): cells preferentially divide toward wound center.
6. **Crowding-driven vertical extrusion**: when neighbor density exceeds 30% of `max_neighbors`, daughters are displaced vertically, building stratified layers.
7. **Stratum field recovery**: differentiating agents write their stratum back into the field each step, visually closing the breach.
8. **Per-cell handoff**: cornified cells dissolve individually after `handoff_delay` steps of stratum stability.
9. **Emergent scar formation**: at dissolution, local collagen concentration determines whether the voxel becomes scar tissue (stratum+5) or normal stratum. See [scar module](../modules/scar/README.md).
10. **Safety timeout**: WoundResolution catches stragglers 200 steps before simulation end or at >90% wound coverage.

## Module cascade

The wound healing response involves coordinated activity across multiple modules. Each module is self-contained with its own README documenting biology, model, parameters, and validation:

| Phase | Timing | Modules involved |
|-------|--------|-----------------|
| Hemostasis / DAMPs | Immediate | [inflammation](../modules/inflammation/README.md) (wound source term) |
| Inflammatory | Day 1 to 5 | [immune](../modules/immune/README.md) (neutrophils, M1 macrophages), [inflammation](../modules/inflammation/README.md) (cytokine field) |
| Proliferative | Day 3 to 14 | [tissue](../modules/tissue/README.md) (keratinocyte migration/division), [fibroblast](../modules/fibroblast/README.md) (TGF-beta/collagen), [perfusion](../modules/perfusion/README.md) + [angiogenesis](../modules/angiogenesis/README.md) (vascular recovery) |
| Provisional matrix | Day 2 to 10 | [fibronectin](../modules/fibronectin/README.md) (migration scaffold), [dermis](../modules/dermis/README.md) (dermal integrity) |
| Remodeling | Day 7+ | [mmp](../modules/mmp/README.md) (ECM degradation), [scar](../modules/scar/README.md) (emergent scar formation) |

## Emergent behaviors

Several system-level behaviors emerge from local cell rules rather than being tuned via global parameters:

- **Inflammation curve**: the peak-and-decay shape emerges from neutrophil wave timing, individual cell age-dependent cytokine tapers, and M2 anti-inflammatory resolution. See [immune module](../modules/immune/README.md).
- **Scar distribution**: scar location and density are driven entirely by where myofibroblasts deposited collagen. Wound margin heals normally; wound center develops scar. See [scar module](../modules/scar/README.md).
- **Wound closure rate**: emerges from the interplay of O2 availability, water hydration, immune pressure suppression, KGF growth factor signaling, fibronectin migration boost, and mechanical crowding.

## Extensions

These features are controlled by per-module parameters and documented in their respective module READMEs:

- **Chemotaxis and efferocytosis**: see [immune module](../modules/immune/README.md)
- **Split pro/anti-inflammatory fields**: see [inflammation module](../modules/inflammation/README.md)
- **Immune pressure field**: see [inflammation module](../modules/inflammation/README.md)
- **Diabetic impairment**: see [diabetic module](../modules/diabetic/README.md) and [diabetic docs](diabetic.md)
- **Biofilm dynamics**: see [biofilm module](../modules/biofilm/README.md)
- **VEGF-driven angiogenesis**: see [angiogenesis module](../modules/angiogenesis/README.md)
