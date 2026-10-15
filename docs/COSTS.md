# Cost boundary

Preflight on 14 October 2026: the active subscription displayed trial upgrade guidance, USD 200 remaining credit, 15 days to credit expiration, current cost 0.00 and forecast 0.00. The previously verified exact trial expiry is 29 October 2026; the portal countdown was consistent with it. The 12-month free-services date is separate. These are provisional portal readings, not a final invoice.

Region: North Europe. Expected incremental cost: USD 0 for one VNet, two subnets and two NSGs without workloads or logging. No metered network appliances, compute, public IPs, storage, peering or traffic are part of the design. The existing NOK 20 alert budget is retained. A budget is not a spending cap.

No upgrade, spending-limit removal, payment authorization, Marketplace item or separately paid feature is permitted. Only the dedicated `rg-atlas-network-20261014` and its resources may be removed by this lab's cleanup.

References checked before creation:
- [VNet pricing](https://azure.microsoft.com/en-us/pricing/details/virtual-network/) distinguishes the free VNet from charged peering and appliances.
- [Microsoft employee NSG cost explanation](https://learn.microsoft.com/en-us/answers/questions/1314374/azure-design-azure-firewall-nsg) distinguishes NSGs from separately charged flow logging.
- [Azure Free Trial terms](https://azure.microsoft.com/en-us/pricing/offers/ms-azr-0044p/) describe the credit and exclusions, including support, Marketplace and separately licensed premium identity products.

The lab does not depend on free VM allowances, a Sentinel trial or a Defender paid plan. No final billing total is inferred from the design estimate.

Post-cleanup check on 15 October 2026: active trial, USD 200 remaining credit, 14 days remaining, current cost 0.00, forecast 0.00, and no active resource usage shown. All three lab resources were deleted. Billing can be delayed; these observations do not certify a final invoice total.
