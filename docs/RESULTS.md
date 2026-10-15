# Verified results

## Azure configuration

| Check | Observed result | Evidence |
|---|---|---|
| Deployment | Portal reported deployment complete on 14 October; name `vnet-atlas-segmentation-1791995710312` | Private portal capture; subsequent resource-state captures |
| Inventory | Exactly one VNet and two NSGs in the dedicated lab group | Private pre-cleanup inventory capture |
| Private subnets | Both subnet JSON definitions have `defaultOutboundAccess: false` | `evidence/vnet-resource.json` |
| NSG bindings | Correct distinct NSG on each subnet, with reciprocal subnet references | All three resource JSON files |
| Rules | Six custom rules in Succeeded state; two SQL allows, four catch-all denies | App/data resource JSON |
| Endpoints | No VM, NIC, database, public IP or packet generator deployed | Lab inventory and resource-state captures |
| Cleanup | Azure success notification for deleted group; view showed 0 of 0 | `evidence/cleanup-observation.txt` |

The raw VNet also records `encryption.enabled: false`; this lab does not claim network encryption. Private-endpoint policy flags are retained as returned, but no private endpoint was deployed or tested.

## Offline new-flow model

The real local run passed 32 configuration checks, all 10 intent-based cases, and four deliberate mutation checks. The [report](../evidence/offline-verification.json) records each selected rule and input hash.

| Scenario | Modeled result |
|---|---|
| App to data, TCP/1433 | Allow at app outbound and data inbound |
| App to data, TCP/1434 | Deny |
| App to data, UDP/1433 | Deny |
| Data to app, new TCP/1433 flow | Deny |
| Outside address to data, TCP/1433 | Deny |
| App to outside address, TCP/443 | Deny |
| App to app, new TCP/1433 flow | Deny |
| Data to outside address, TCP/443 | Deny |
| Data to data, new TCP/1433 flow | Deny |
| Outside address to app, TCP/22 | Deny |

The outside addresses are documentation addresses used only in local fixtures. They are not destinations of test traffic. A modeled inbound flow does not imply a public route exists.

Mutation checks removed the app SQL allow, widened both allow destination ports, changed the app outbound deny into an allow, and enabled default outbound access in a copied configuration. Configuration checks caught all four. Flow cases also caught the first three. The private-subnet mutation is caught by configuration checks only: the model does not simulate internet reachability. No mutation was sent to Azure.

## Debugging finding

The first local run passed 30/32 configuration checks. Both failures were reciprocal subnet references: NSG responses used uppercase resource path names while the VNet response used lowercase names. The validator now compares these resource IDs case-insensitively, consistent with [Microsoft's resource naming documentation](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/resource-name-rules). The source evidence remains unchanged. The corrected run passed 32/32.

## Boundaries

- Actual packet filtering, SQL connectivity, return traffic and workload availability were not tested.
- Azure NSGs are stateful; the local model handles new-flow decisions only. A reply to an established allowed flow is not modeled as a fresh reverse connection.
- The model excludes Azure platform exceptions, DNS/IMDS behavior, service tags, routes, Network Manager admin rules, NIC-level rules, IPv6 and established flows. Unsupported rule forms raise an error; it is not a general Azure NSG simulator.
- Default NSG rules remain in the captures. The model evaluates custom rules only; catch-all custom denies match ordinary modeled flows before the default rules. This does not establish behavior for Azure platform exceptions.
- No ARM/Bicep deployment test or Network Watcher connectivity test is claimed.

For rule processing and platform limitations, see [Microsoft's NSG overview](https://learn.microsoft.com/en-us/azure/virtual-network/network-security-groups-overview).
