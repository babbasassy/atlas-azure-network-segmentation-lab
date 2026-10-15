# Cleanup completed

On 15 October 2026, after the resource JSON and rule screens were captured, the portal deletion review listed exactly:

- `nsg-atlas-app`
- `nsg-atlas-data`
- `vnet-atlas-segmentation`

Deletion was scoped to the disposable lab group `rg-atlas-network-20261014`. Azure subsequently reported **Deleted resource group rg-atlas-network-20261014**, and the resource view showed **0 of 0**. The confirming capture was saved at 11:25:26 UTC. See the [sanitized observation](../evidence/cleanup-observation.txt).

No workload disks, compute, public IPs, storage, logging pipelines, paid network appliances or identities were created by this lab. Existing user resources were not deleted. The previously configured subscription alert budget remains; it is an alert mechanism, not a hard spending cap.

Post-cleanup subscription overview: active trial, USD 200 remaining credit, 14 days to expiry, current cost 0.00 and forecast 0.00. These values are provisional portal readings. No upgrade, removal of the spending limit or personal payment was performed.

There are no resources from this network lab to keep running until trial expiry. Reproduction requires a new explicitly scoped disposable environment and a fresh cost/credit check.
