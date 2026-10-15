"""Offline checks of captured configuration. Does not contact Azure or send packets."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = {'app': 'app-nsg-resource.json', 'data': 'data-nsg-resource.json', 'vnet': 'vnet-resource.json'}
PREFIX = {'app': '10.42.1.0/24', 'data': '10.42.2.0/24'}

def load():
    return {k: json.loads((ROOT / 'evidence' / v).read_text()) for k, v in FILES.items()}

def config_checks(objects):
    results = []
    def check(name, condition):
        results.append({'check': name, 'passed': bool(condition)})
    vnet = objects['vnet']
    vp = vnet['properties']
    check('VNet address space', vp['addressSpace']['addressPrefixes'] == ['10.42.0.0/16'])
    check('Exactly two named subnets', sorted(s['name'] for s in vp['subnets']) == ['snet-app', 'snet-data'])
    check('No peering or paid DDoS plan configured', not vp.get('virtualNetworkPeerings') and vp.get('enableDdosProtection') is False and not vp.get('ddosProtectionPlan'))
    for key, obj in objects.items():
        check(f'{key}: succeeded in North Europe with lab tag', obj['properties']['provisioningState'] == 'Succeeded' and obj['location'] == 'northeurope' and obj['tags'].get('LabPurpose') == 'ATLAS-Network-Segmentation')
    subnets = {s['name']: s for s in vp['subnets']}
    for tier in PREFIX:
        sn = subnets.get('snet-' + tier, {})
        sp = sn.get('properties', {})
        check(f'{tier}: subnet prefix', sp.get('addressPrefixes') == [PREFIX[tier]])
        check(f'{tier}: default outbound disabled', sp.get('defaultOutboundAccess') is False)
        check(f'{tier}: correct NSG binding', sp.get('networkSecurityGroup', {}).get('id', '').casefold() == objects[tier]['id'].casefold())
        check(f'{tier}: no NAT or attached IP configurations', not sp.get('natGateway') and not sp.get('ipConfigurations') and not sp.get('delegations'))
        np = objects[tier]['properties']
        # Azure returned uppercase subnet path components in the NSG response.
        # ARM names for these resource types are case-insensitive; keep raw casing in evidence.
        check(f'{tier}: reciprocal subnet binding', [s['id'].casefold() for s in np.get('subnets', [])] == [sn.get('id', '').casefold()])
        check(f'{tier}: no NIC binding', not np.get('networkInterfaces'))
        rules = np['securityRules']
        check(f'{tier}: exactly three custom rules', len(rules) == 3)
        check(f'{tier}: unique direction-priority pairs', len({(r['properties']['direction'], r['properties']['priority']) for r in rules}) == len(rules))
        check(f'{tier}: all custom rules provisioned', all(r['properties']['provisioningState'] == 'Succeeded' for r in rules))
        allow = [r['properties'] for r in rules if r['properties']['access'] == 'Allow']
        expected = dict(direction='Outbound' if tier == 'app' else 'Inbound', priority=100, protocol='TCP', access='Allow', sourceAddressPrefix=PREFIX['app'], destinationAddressPrefix=PREFIX['data'], sourcePortRange='*', destinationPortRange='1433')
        check(f'{tier}: exactly the intended SQL allow', len(allow) == 1 and all(allow[0].get(k) == v for k, v in expected.items()))
        for direction in ['Inbound', 'Outbound']:
            denies = [r['properties'] for r in rules if r['properties']['access'] == 'Deny' and r['properties']['direction'] == direction]
            check(f'{tier}: catch-all {direction} deny at 1000', len(denies) == 1 and denies[0]['priority'] == 1000 and all(denies[0].get(k) == '*' for k in ['protocol', 'sourceAddressPrefix', 'destinationAddressPrefix', 'sourcePortRange', 'destinationPortRange']))
        check(f'{tier}: custom rules precede defaults', bool(np['defaultSecurityRules']) and max(r['properties']['priority'] for r in rules) < min(r['properties']['priority'] for r in np['defaultSecurityRules']))
    return results

def address_matches(prefix, address):
    return prefix == '*' or ipaddress.ip_address(address) in ipaddress.ip_network(prefix)

def port_matches(spec, port):
    if spec == '*':
        return True
    if '-' in spec:
        low, high = map(int, spec.split('-'))
        return low <= port <= high
    return int(spec) == port

def decision(nsg, direction, flow):
    """Only the custom IPv4/CIDR rules in these captures; fail on unsupported rules."""
    rules = sorted(nsg['properties']['securityRules'], key=lambda r: r['properties']['priority'])
    for r in rules:
        p = r['properties']
        if p['direction'] != direction:
            continue
        if any(p.get(k) for k in ['sourcePortRanges', 'destinationPortRanges', 'sourceAddressPrefixes', 'destinationAddressPrefixes', 'sourceApplicationSecurityGroups', 'destinationApplicationSecurityGroups']):
            raise ValueError('Augmented/ASG rules are outside this model')
        for k in ['sourceAddressPrefix', 'destinationAddressPrefix']:
            if p[k] != '*':
                if ipaddress.ip_network(p[k]).version != 4:
                    raise ValueError('Only IPv4 is modeled')
        if p['protocol'].upper() not in {'*', 'TCP', 'UDP'}:
            raise ValueError('Unsupported rule protocol')
        if p['access'] not in {'Allow', 'Deny'}:
            raise ValueError('Unsupported access decision')
        if (p['protocol'] == '*' or p['protocol'].upper() == flow['protocol'].upper()) and address_matches(p['sourceAddressPrefix'], flow['source']) and address_matches(p['destinationAddressPrefix'], flow['destination']) and port_matches(p['sourcePortRange'], flow['source_port']) and port_matches(p['destinationPortRange'], flow['destination_port']):
            return {'access': p['access'], 'rule': r['name'], 'priority': p['priority']}
    raise ValueError('No custom rule matched: default rules are not modeled')

def flow_decision(objects, flow):
    if flow['protocol'].upper() not in {'TCP', 'UDP'} or any(ipaddress.ip_address(flow[k]).version != 4 for k in ['source', 'destination']):
        raise ValueError('Only ordinary IPv4 TCP/UDP new flows are modeled')
    if any(not 0 <= flow[k] <= 65535 for k in ['source_port', 'destination_port']):
        raise ValueError('Port outside valid range')
    stages = []
    for field, direction in [('source', 'Outbound'), ('destination', 'Inbound')]:
        for tier, cidr in PREFIX.items():
            if address_matches(cidr, flow[field]):
                stages.append({'tier': tier, 'direction': direction, **decision(objects[tier], direction, flow)})
    if not stages:
        raise ValueError('Flow has no endpoint in a modeled subnet')
    return {'access': 'Allow' if all(s['access'] == 'Allow' for s in stages) else 'Deny', 'stages': stages}

def mutation_checks(objects, flows):
    results = []
    for name in ['remove-app-allow', 'widen-both-allow-ports', 'allow-app-egress', 'enable-default-outbound']:
        mutated = copy.deepcopy(objects)
        if name == 'remove-app-allow':
            mutated['app']['properties']['securityRules'] = [r for r in mutated['app']['properties']['securityRules'] if r['properties']['access'] != 'Allow']
        elif name == 'widen-both-allow-ports':
            for tier in PREFIX:
                for r in mutated[tier]['properties']['securityRules']:
                    if r['properties']['access'] == 'Allow':
                        r['properties']['destinationPortRange'] = '*'
        elif name == 'allow-app-egress':
            for r in mutated['app']['properties']['securityRules']:
                if r['name'] == 'Deny-All-Outbound':
                    r['properties']['access'] = 'Allow'
        else:
            mutated['vnet']['properties']['subnets'][0]['properties']['defaultOutboundAccess'] = True
        detected = [c['check'] for c in config_checks(mutated) if not c['passed']]
        mismatches = [f['name'] for f in flows if flow_decision(mutated, f)['access'] != f['expected']]
        results.append({'mutation': name, 'caught_by_config': detected, 'flow_mismatches': mismatches, 'passed': bool(detected) and (name == 'enable-default-outbound' or bool(mismatches))})
    return results

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    objects = load()
    flows = json.loads((ROOT / 'tests/flows.json').read_text())
    checks = config_checks(objects)
    decisions = []
    for flow in flows:
        outcome = flow_decision(objects, flow)
        decisions.append({**flow, **outcome, 'passed': outcome['access'] == flow['expected']})
    mutations = mutation_checks(objects, flows)
    passed = all(r['passed'] for r in checks + decisions + mutations)
    report = {'generated_at_utc': datetime.now(timezone.utc).isoformat(), 'evidence_type': 'offline evaluation of sanitized portal configuration; no packets or Azure API calls', 'source_sha256': {f: hashlib.sha256((ROOT / 'evidence' / f).read_bytes()).hexdigest() for f in FILES.values()}, 'passed': passed, 'configuration_checks': checks, 'modeled_flows': decisions, 'mutation_checks': mutations}
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f"{'PASS' if passed else 'FAIL'}: {sum(c['passed'] for c in checks)}/{len(checks)} configuration checks, {sum(f['passed'] for f in decisions)}/{len(decisions)} modeled flows, {sum(m['passed'] for m in mutations)}/{len(mutations)} mutations detected")
    return 0 if passed else 1

if __name__ == '__main__':
    raise SystemExit(main())
