# ansible-arubaos

Ansible modules for Aruba Networks (HPE procurve) switching.

Current modules:
* ArubaOSIP: configures IP address on VLANs.
* ArubaOSVlanPorts: configure vlans as tagged/untagged on ports.
* ArubaOSVlans: create, delete, or modify Vlans.

Requirements
------------
pyarubaoss python library forked as one of my repositories.
Devices must run verison 16+ of code and have REST interface enabled. (REST is enabled by default).
