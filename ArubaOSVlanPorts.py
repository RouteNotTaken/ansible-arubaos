#!/usr/bin/python
# Copyright (c) 2017 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'
}


DOCUMENTATION = """
---
module: ArubaOSVlans
version_added: "0.1"
author: "RouteNotTaken"
short_description: Manage VLANs on Aruba OS (hpe procruve) network devices
description:
  - Manage VLANs via ArubaOS API
notes:
  - Tested against 16.03.0005
options:
  name:
    description:
      - Name of the VLAN.
  vlan_id:
    description:
      - ID of the VLAN.
    required: true
  aggregate:
    description: List of VLANs definitions.
  state:
    description:
      - State of the VLAN configuration.
    default: present
    choices: ['present', 'absent']
"""

EXAMPLES = """
- name: Create vlan
  ArubaOSVlans:
    vlan_id: 4000
    name: vlan-4000
    state: present

- name: Create aggregate of vlans
  ArubaOSVlans:
    aggregate:
      - vlan_id: 4000
      - {vlan_id: 4001, name: vlan-4001}
"""

from ansible.module_utils.basic import AnsibleModule
from copy import deepcopy


try:
    from pyarubaoss import auth, vlans
    has_lib = True
except ImportError:
    has_lib = False


def generate_payloads((want, have)):
    want, have = (want, have)
    changed_ports = want[:]

    for w in want:
        for h in have:
            if all(w[k] == h[k] for k in w.keys()):
                changed_ports.remove(w)
                break

    return changed_ports


def current_ports(device):
    current_ports = []
    output = vlans.get_vlan_ports(device)
    current_ports = output['vlan_port_element'] 

    return current_ports


def wanted_ports(module):
    wanted_ports = []
    aggregate = module.params.get('aggregate')
    if aggregate:
        for item in aggregate:
            d = item.copy()

            wanted_ports.append(d)
    else:
        wanted_ports.append({
            'vlan_id': module.params['vlan_id'],
            'port_id': module.params['port_id'],
            'port_mode': module.params['port_mode'],
        })
    for w in wanted_ports:
        if w['port_mode'] == 'tagged':
            w['port_mode'] = 'POM_TAGGED_STATIC'
        else:
            w['port_mode'] = 'POM_UNTAGGED'

    return wanted_ports


def main():
    provider_spec = {
        'host': {'required': True, 'type': 'str'},
        'username': {'required': True, 'type': 'str'},
        'password': {'required': True, 'type': 'str', 'no_log': True},
        'version': {'default': 'v1', 'type': 'str'},
    }
    element_spec = {
        'vlan_id': {'type': 'int'},
        'port_id': {},
        'port_mode': {'default': 'untagged', 'choices': ['tagged', 'untagged']},
    }

    aggregate_spec = deepcopy(element_spec)
    aggregate_spec['vlan_id'] = {'required': True}
    aggregate_spec['port_id'] = {'required': True}
    aggregate_spec['port_mode'] = {'required': True}

    # remove default in aggregate spec, to handle common arguments
    #remove_default_spec(aggregate_spec)

    argument_spec = dict(
        aggregate=dict(type='list', elements='dict', options=aggregate_spec)
    )

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

    want = wanted_ports(module)
    have = current_ports(device)

    ports_changed = generate_payloads((want,have))

    if ports_changed:
        if not module.check_mode:
            for p in ports_changed:
                vlans.set_vlan_ports(device, p['vlan_id'], p['port_id'], p['port_mode']) 

        result['changed'] = True

    device.logout()
    module.exit_json(**result)


if __name__ == '__main__':
    main()
