# Reproduction runbook

This documents the portal workflow used in the lab. The captured JSON is a reference, not a deployable ARM template. Running the offline verifier requires no Azure resources.

## Before deployment

Verify the subscription's offer, active status, remaining credit, actual credit expiry and spending protection. Review current [VNet pricing](https://azure.microsoft.com/en-us/pricing/details/virtual-network/) and [trial terms](https://azure.microsoft.com/en-us/pricing/offers/ms-azr-0044p/). Use a dedicated disposable resource group and a region allowed by the subscription. Do not upgrade the subscription or enable paid add-ons to reproduce this exercise.

## Portal configuration

1. Create the dedicated group in North Europe. The executed lab used `rg-atlas-network-20261014` and tag `LabPurpose=ATLAS-Network-Segmentation`.
2. Create two empty NSGs named `nsg-atlas-app` and `nsg-atlas-data` in that group, with the same tag.
3. Create `vnet-atlas-segmentation`, address space `10.42.0.0/16`. Replace the proposed default subnet with `snet-app` (`10.42.1.0/24`) and `snet-data` (`10.42.2.0/24`). Mark both private so default outbound access is disabled. Bind each to its corresponding NSG.
4. Keep NAT, Bastion, Firewall, paid DDoS, public IPs, peering and flow logging disabled or absent. Review the complete resource list before creating the VNet.
5. Add the six rules in [DESIGN.md](DESIGN.md). The source port is `*` in every rule. Set both SQL allows to priority 100 and every catch-all deny to priority 1000. Inbound and outbound can each use priority 1000 because they are separate directions.
6. Inspect each NSG's rules, subnet association and provisioning state. Inspect the VNet subnet bindings and default outbound settings in JSON View. Record configuration evidence before any deletion.

The temporary empty NSGs contained Azure defaults before the custom rules were added. There were no endpoints or workloads during that interval. A production deployment needs a controlled rollout strategy and meaningful traffic tests.

## Validate without making traffic claims

Capture each resource's JSON View through the portal, redact private subscription identifiers, etags and resource GUIDs, and retain the original privately. Compare the captured configuration with the intended matrix. Run `python scripts/verify.py` against the supplied repository evidence to reproduce the offline model results.

For a different capture, update the fixtures and design intentionally; do not alter expected results merely to hide a real configuration mismatch. Evidence with unsupported rule forms is outside the narrow model's scope.

## Finish

Review the dedicated group's exact inventory, delete only the disposable lab group, wait for Azure's success notification and check the empty view. Record the result and recheck credit/cost information. Never leave billable experiment components running until a later work session.
