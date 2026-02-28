> [Home](../README.md) / [Docs](README.md) / Tumor

# Tumor Module

Self-contained BCC (basal cell carcinoma) growth module. Enable with `[skin.tumor] enabled = true` or `--preset=tumor`. See also: [Guide](guide.md) | [Parameters](parameters.md) | [Architecture](architecture.md)

For the full mechanistic model, parameters with literature sources, and validation datasets, see the [tumor module README](../modules/tumor/README.md).

## Tumor cells vs normal keratinocytes

| Aspect | Normal keratinocyte | Tumor cell |
|--------|-------------------|------------|
| Cycle duration | 17h total | Scaled by `tumor_cycle_factor` (default 3.3x = ~56h, BCC) |
| Contact inhibition | Hard threshold at max_neighbors=14 | Soft CI: `p = 1 - (n/12)^s`, s=`tumor_ci_steepness` (YAP/TAZ) |
| Apoptosis | TA exhaustion only | Per-step probability `tumor_apoptosis_rate` (BCC cell loss factor) |
| Division limit | Stem: unlimited, TA: 4 | Unlimited always |
| Stratum gating | Only basal divides | Divides at any position |
| Calcium response | Drives differentiation | Ignored |
| O2 dependency | Suppresses below threshold | Same |
| Continuum handoff | Cornified cells dissolve after handoff_delay | G0 cells dissolve after tumor_handoff_delay |

## Scenario composability

Wound and tumor modules are independent. Combine them freely via config or presets:

| Scenario | Preset |
|----------|--------|
| Nothing | `--preset=nothing` |
| Wound only | `--preset=wound` |
| Tumor only | `--preset=tumor` |
| Tumor then wound | `--preset=tumor_wound` |
