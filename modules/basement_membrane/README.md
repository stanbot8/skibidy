# Basement membrane integrity

This opt-in extension models the capacity of assembled basement membrane to
anchor basal stem cells. The baseline remains disabled. Enabling it adds a
dimensionless integrity field B in [0,1] on the structural grid slice containing
z=0; other slices are zero. Healthy tissue starts at B=1. Each wound event removes
the configured fraction of integrity inside its supplied cylinder.

The consumer is the stem-cell anchoring rule in `Differentiation`. At B=1 it
performs the existing height correction to half the cell diameter. At B=0 it
allows existing mechanics to displace the cell above that height. Intermediate
integrity corrects fraction B of the displacement at each behavior invocation.
This linear attachment response is a modeling assumption, with timestep-sensitive
partial attachment. The geometric z>=0 boundary still applies; this extension
does not represent dermal invasion, an integrin force law, or membrane permeability.

Local basal keratinocytes restore integrity with dB/dt=k C (1-B). C is the maximum
of explicit basal-agent occupancy and the local basal continuum fraction, sampled
in world coordinates when grid resolutions differ. This avoids counting agent
and continuum occupancy twice. Repair is absent without local basal coverage.
The exact exponential update keeps B bounded for large timesteps. One basal agent
marks its structural column occupied; this occupancy approximation depends on
structural grid resolution and requires a resolution sensitivity check.

`wound_damage=1` and `repair_rate=0.005` per hour are explicit research assumptions,
not measured coefficients or fitted human wound values. The latter gives a
200-hour time constant at full coverage. Zero repair is supported. Compare zero
and partial damage and independently vary repair rate, timestep, and structural
resolution before interpreting outcomes. Existing calibrated parameters are unchanged.

Kariya et al. studied normal human keratinocytes and found that assembled
laminin-332 matrices promote stable adhesion, while soluble laminin-332 has
different motility effects. This supports the attachment direction but neither
our integrity scale nor its numeric response. Migration is therefore not
multiplied by integrity. [Primary study, PLOS ONE 2012](https://doi.org/10.1371/journal.pone.0035546).

Germain et al. sampled grafts of cultured human epidermal sheets on athymic mice
at 2, 4 and 21 days. Laminin and bullous pemphigoid antigens were nearly continuous
at day 2, when collagen IV was generally absent; collagen IV was detected at day 4.
Lamina densa was discontinuous at day 2 and continuous with anchoring structures
at day 21. Collagen VII labeling increased over days 2–21. These distinct component
milestones support gradual assembly but cannot identify one exponential
integrity rate. The public abstract gives no numeric coverage, sample size or
variance. The authors also distinguish this graft context from other wound
models. [Primary study, 1995](https://pubmed.ncbi.nlm.nih.gov/7794497/).
The manually extracted [timing table](data/germain1995_timing.csv) and
[provenance](data/provenance.json) retain that qualitative measurement definition;
no percentage is inferred from terms such as continuous or detected.

The assessment lead Jiang et al. (2025), DOI 10.1038/s41467-025-58906-z, studies
fibromodulin and IL-1β-dependent myofibroblast apoptosis. It does not establish
basement membrane attachment or repair kinetics and is not used to parameterize
this extension. [Primary study](https://pubmed.ncbi.nlm.nih.gov/40221432/).

Enable at startup through `[skin.basement_membrane]` in the module configuration
or an experiment override. The field is initialized, wounded, and updated by the
composite-field owner. Disabled runs create no field and consume no random draws.
