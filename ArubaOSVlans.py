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

try:
    from pyarubaoss import auth, vlans
    has_lib = True
except ImportError:
    has_lib = False


def search_obj_in_list(vlan_id, list):
    for o in list:
        if o['vlan_id'] == vlan_id:
            return o


def generate_payloads((want,have)):
    want, have = (want,have)
    changed_vlans = []

    for w in want:
        obj_in_have = search_obj_in_list(w['vlan_id'], have)
        if not w.get('state'):
            w['state'] = 'present'
        if w['state'] == 'absent':
            if obj_in_have:
                w['action'] = [vlans.delete_vlan, 'del']
            else:
                continue
        elif w['state'] == 'present':
            w['vlan_name'] = w.get('vlan_name','')
            if obj_in_have:
                w['action'] = [vlans.modify_vlan, 'mod']
                continue
            else:
                w['action'] = [vlans.create_vlan, 'create']

        if w['action']:
            changed_vlans.append(w)

    return changed_vlans


def current_vlans(device):
    ### checks current vlan table (show vlan) and returns vlans as objects
    c_vlans = []
    output = vlans.get_vlans(device)
    for vlan in output:
        obj = {}
        obj['vlan_id'] = vlan['vlan_id']
        obj['vlan_name'] = vlan['name']

        c_vlans.append(obj)

    return c_vlans

def wanted_vlans(module):
    w_vlans = []
    aggregate = module.params.get('aggregate')
    if aggregate:
        for item in aggregate:
            d = item.copy()

            w_vlans.append(d)
    else:
        w_vlans.append({
            'vlan_id': module.params['vlan_id'],
            'vlan_name': module.params.get('vlan_name', 'default'),
            'state': module.params['state'],
        })

    return w_vlans


def main():
    vlan_specs = {
        'vlan_id': {'type': 'int'},
        'vlan_name': {'type': 'str'},
        'state': {'default': 'present', 'choices': ['present', 'absent']},
    }
    specs = {
        'host': {'required': True, 'type': 'str'},
        'username': {'required': True, 'type': 'str'},
        'password': {'required': True, 'type': 'str'},
        'version': {'default': 'v1', 'type': 'str'},
        'aggregate': {'type': 'list', 'elements': 'dict', 'options': vlan_specs}
    }
    specs.update(vlan_specs)
    required_one_of = [['vlan_id', 'aggregate']]
    mutually_exclusive = [['vlan_id', 'aggregate']]

    module = AnsibleModule(
        argument_spec = specs,
        supports_check_mode = True,
        required_one_of = required_one_of,
        mutually_exclusive = mutually_exclusive,
        no_log = True,
    )

    if not has_lib:
        module.fail_json(msg='pyarubaoss required for this module')
    warnings = []
    result = {'changed': False}

    if warnings:
        result['warnings'] = warnings

    args = module.params
    host = args['host']
    username = args['username']
    password = args['password']
    version = args['version']
    state = args['state']

    device = auth.AOSSAuth(host, username, password, 'v1')

    want = wanted_vlans(module)
    have = current_vlans(device)

    vlans_changed = generate_payloads((want,have))

    if vlans_changed:
        if not module.check_mode:
            for v in vlans_changed:
                if v['action'][1] == 'del':
                    v['action'][0](device, v['vlan_id'])
                else:
                    v['action'][0](device, v['vlan_id'], v['vlan_name'])

        result['changed'] = True

    device.logout()
    module.exit_json(**result)


if __name__ == '__main__':
    main()
