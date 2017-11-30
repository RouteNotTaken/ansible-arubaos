#!/usr/bin/python
# Copyright (c) 2017 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'
}


DOCUMENTATION = """
---
module: ArubaOSVlanPorts
version_added: "0.1"
author: "RouteNotTaken"
short_description: Manage VLAN ip address assignments on Aruba OS (hpe procruve) network devices
description:
  - Manage VLAN ip address assignments via ArubaOS API
notes:
  - Tested against 16.03.0005
options:
  vlan_id:
    description:
      - ID of the VLAN
    required: true
  ip_address:
    description:
      - ip address
  ip_mask:
    description:
      - subnet mask (dotted)
  aggregate:
    description: List of ip addresses and VLAN assignments.
"""

EXAMPLES = """
- name: Assign ip address 10.200.0.1/24 to vlan 200
  ArubaOSIP:
    vlan_id: 200
    ip_address: '10.200.0.1'
    ip_mask: '255.255.255.0'

- name: Assign ip address 10.x.0.1/24 to vlans 200-202
  ArubaOSVlanPorts:
    aggregate:
      - {vlan_id: 200, ip_address: '10.200.0.1', ip_mask: '255.255.255.0'}
      - {vlan_id: 201, ip_address: '10.201.0.1', ip_mask: '255.255.255.0'}
      - {vlan_id: 202, ip_address: '10.202.0.1', ip_mask: '255.255.255.0'}
"""

from ansible.module_utils.basic import AnsibleModule
from copy import deepcopy


try:
    from pyarubaoss import auth, ip
    has_lib = True
except ImportError:
    has_lib = False


def generate_payloads((want, have)):
    want, have = (want, have)
    changed_ips = want[:]

    for w in want:
        for h in have:
            if all(w[k] == h[k] for k in w.keys()):
                changed_ips.remove(w)
                break

    return changed_ips


def current_ips(device):
    current_ips = []
    output = ip.get_ipaddresses(device)
    current_ips = output

    return current_ips


def wanted_ips(module):
    wanted_ips = []
    aggregate = module.params.get('aggregate')
    if aggregate:
        for item in aggregate:
            d = item.copy()
            d['ip_address'] = {
                    'octets': item['ip_address'],
                    'version': 'IAV_IP_V4'
            }
            d['ip_mask'] = {
                    'octets': item['ip_mask'],
                    'version': 'IAV_IP_V4'
            }
            wanted_ips.append(d)
    else:
        wanted_ips.append({
            'vlan_id': module.params['vlan_id'],
            'ip_address': {
                'octets': module.params['ip_address'],
                'version': 'IAV_IP_V4'
            },
            'ip_mask': {
                'octets': module.params['ip_mask'],
                'version': 'IAV_IP_V4'
            },
        })

    return wanted_ips


def main():
    provider_spec = {
        'host': {'required': True, 'type': 'str'},
        'username': {'required': True, 'type': 'str'},
        'password': {'required': True, 'type': 'str', 'no_log': True},
        'version': {'default': 'v1', 'type': 'str'},
    }
    element_spec = {
        'vlan_id': {'type': 'int'},
        'ip_address': {},
        'ip_mask': {},
    }

    aggregate_spec = deepcopy(element_spec)
    aggregate_spec['vlan_id'] = {'required': True}
    aggregate_spec['ip_address'] = {'required': True}
    aggregate_spec['ip_mask'] = {'required': True}

    argument_spec = {
            'aggregate': {
                'type': 'list',
                'elements': 'dict',
                'options': aggregate_spec
            }
    }

    argument_spec.update(element_spec)
    argument_spec.update(provider_spec)

    required_one_of = [['aggregate', 'vlan_id']]
    mutually_exclusive = [['aggregate', 'vlan_id']]

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=required_one_of,
        mutually_exclusive=mutually_exclusive,
        supports_check_mode=True
    )

    if not has_lib:
        module.fail_json(msg='pyarubaoss required for this module')
    warnings = []
    result = {'changed': False}

    args = module.params
    host = args['host']
    username = args['username']
    password = args['password']
    version = args['version']

    device = auth.AOSSAuth(host, username, password, 'v1')

    want = wanted_ips(module)
    have = current_ips(device)

    ips_changed = generate_payloads((want,have))

    if ips_changed:
        if not module.check_mode:
            for i in ips_changed:
                ip.del_ipaddresses(device, i['vlan_id'])
                ip.set_ipaddresses(device, i['vlan_id'], i['ip_address']['octets'], i['ip_mask']['octets'])

        result['changed'] = True

    device.logout()
    module.exit_json(**result)


if __name__ == '__main__':
    main()
