# Copyright 2014 OpenStack LLC.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock
import six

from infoblox_client import exceptions
from infoblox_client import object_manager as om
from infoblox_client import objects
from infoblox_client.tests import base


class PayloadMatcher(object):
    ANYKEY = 'MATCH_ANY_KEY'

    def __init__(self, expected_values):
        self.args = expected_values

    def __eq__(self, actual):
        expected = []

        for key, expected_value in six.iteritems(self.args):
            expected.append(self._verify_value_is_expected(actual, key,
                                                           expected_value))

        return all(expected)

    def __repr__(self):
        return "Expected args: %s" % self.args

    def _verify_value_is_expected(self, d, key, expected_value):
        found = False
        if not isinstance(d, dict):
            return False

        for k in d:
            if isinstance(d[k], dict):
                found = self._verify_value_is_expected(d[k], key,
                                                       expected_value)
            if isinstance(d[k], list):
                if k == key and d[k] == expected_value:
                    return True
                for el in d[k]:
                    found = self._verify_value_is_expected(el, key,
                                                           expected_value)

                    if found:
                        return True
            if (key == k or key == self.ANYKEY) and d[k] == expected_value:
                return True
        return found


class ObjectManipulatorTestCase(base.TestCase):
    EXT_ATTRS = {'Tenant ID': {'value': '40501209848593'}}

    def test_create_net_view_creates_network_view_object(self):
        connector = mock.Mock()
        connector.get_object.return_value = None
        connector.create_object.return_value = None

        ibom = om.InfobloxObjectManager(connector)

        net_view_name = 'test_net_view_name'
        ibom.create_network_view(net_view_name, self.EXT_ATTRS)

        get_matcher = PayloadMatcher({'name': net_view_name})
        create_matcher = PayloadMatcher({'name': net_view_name,
                                         'extattrs': self.EXT_ATTRS})
        connector.get_object.assert_called_once_with(
            'networkview', get_matcher, return_fields=mock.ANY)
        connector.create_object.assert_called_once_with(
            'networkview', create_matcher, mock.ANY)

    def test_create_host_record_creates_host_record_object(self):
        dns_view_name = 'test_dns_view_name'
        zone_auth = 'test.dns.zone.com'
        hostname = 'test_hostname'
        ip = '192.168.0.1'
        mac = 'aa:bb:cc:dd:ee:ff'
        use_dhcp = True

        host_record = {'_ref': 'host_record_ref'}
        connector = mock.Mock()
        connector.create_object.return_value = host_record

        ibom = om.InfobloxObjectManager(connector)

        ibom.create_host_record_for_given_ip(dns_view_name, zone_auth,
                                             hostname, mac, ip, self.EXT_ATTRS,
                                             use_dhcp)

        exp_payload = {
            'name': 'test_hostname.test.dns.zone.com',
            'view': dns_view_name,
            'extattrs': self.EXT_ATTRS,
            'ipv4addrs': [
                {'mac': mac, 'configure_for_dhcp': True, 'ipv4addr': ip}
            ]
        }

        connector.create_object.assert_called_once_with('record:host',
                                                        exp_payload,
                                                        mock.ANY)

    def test_create_host_record_range_create_host_record_object(self):
        dns_view_name = 'test_dns_view_name'
        zone_auth = 'test.dns.zone.com'
        hostname = 'test_hostname'
        mac = 'aa:bb:cc:dd:ee:ff'
        net_view_name = 'test_net_view_name'
        first_ip = '192.168.0.1'
        last_ip = '192.168.0.254'

        host_record = {'_ref': 'host_record_ref'}
        connector = mock.Mock()
        connector.create_object.return_value = host_record

        ibom = om.InfobloxObjectManager(connector)

        ibom.create_host_record_from_range(
            dns_view_name, net_view_name, zone_auth, hostname, mac, first_ip,
            last_ip, self.EXT_ATTRS, True)

        next_ip = \
            'func:nextavailableip:192.168.0.1-192.168.0.254,test_net_view_name'
        exp_payload = {
            'name': 'test_hostname.test.dns.zone.com',
            'view': dns_view_name,
            'extattrs': self.EXT_ATTRS,
            'ipv4addrs': [
                {'mac': mac, 'configure_for_dhcp': True, 'ipv4addr': next_ip}
            ]
        }
        connector.create_object.assert_called_once_with(
            'record:host', exp_payload, mock.ANY)

    def test_delete_host_record_deletes_host_record_object(self):
        connector = mock.Mock()
        connector.get_object.return_value = mock.MagicMock()

        ibom = om.InfobloxObjectManager(connector)

        dns_view_name = 'test_dns_view_name'
        ip_address = '192.168.0.254'

        ibom.delete_host_record(dns_view_name, ip_address)

        matcher = PayloadMatcher({'view': dns_view_name,
                                  PayloadMatcher.ANYKEY: ip_address})
        connector.get_object.assert_called_once_with(
            'record:host', matcher, extattrs=None,
            force_proxy=mock.ANY, return_fields=mock.ANY)
        connector.delete_object.assert_called_once_with(mock.ANY)

    def test_get_network_gets_network_object(self):
        connector = mock.Mock()
        connector.get_object.return_value = mock.MagicMock()

        ibom = om.InfobloxObjectManager(connector)

        net_view_name = 'test_dns_view_name'
        cidr = '192.168.0.0/24'

        ibom.get_network(net_view_name, cidr)

        matcher = PayloadMatcher({'network_view': net_view_name,
                                  'network': cidr})
        connector.get_object.assert_called_once_with(
            'network', matcher, extattrs=None,
            force_proxy=mock.ANY, return_fields=mock.ANY)

    def test_throws_network_not_available_on_get_network(self):
        connector = mock.Mock()
        connector.get_object.return_value = None

        ibom = om.InfobloxObjectManager(connector)

        net_view_name = 'test_dns_view_name'
        cidr = '192.168.0.0/24'

        self.assertRaises(exceptions.InfobloxNetworkNotAvailable,
                          ibom.get_network, net_view_name, cidr)

        matcher = PayloadMatcher({'network_view': net_view_name,
                                  'network': cidr})
        connector.get_object.assert_called_once_with('network',
                                                     matcher,
                                                     extattrs=mock.ANY,
                                                     force_proxy=mock.ANY,
                                                     return_fields=mock.ANY)

    def test_object_is_not_created_if_already_exists(self):
        net_view_name = 'test_dns_view_name'
        connector = mock.Mock()
        connector.create_object.return_value = mock.MagicMock()
        connector.get_object.return_value = [{
            '_ref': 'object-reference',
            'name': net_view_name}]

        ibom = om.InfobloxObjectManager(connector)
        ibom.create_network_view(net_view_name, self.EXT_ATTRS)

        matcher = PayloadMatcher({'name': net_view_name})
        connector.get_object.assert_called_once_with(
            'networkview', matcher, return_fields=mock.ANY)
        assert not connector.create_object.called

    def test_get_member_gets_member_object(self):
        connector = mock.Mock()
        connector.get_object.return_value = None
        ibom = om.InfobloxObjectManager(connector)
        member = objects.Member(connector, name='member1', ip='some-ip')

        ibom.get_member(member)

        matcher = PayloadMatcher({'host_name': member.name})
        connector.get_object.assert_called_once_with('member', matcher,
                                                     return_fields=mock.ANY)

    def test_restart_services_calls_infoblox_function(self):
        connector = mock.Mock()
        connector.get_object.return_value = mock.MagicMock()
        ibom = om.InfobloxObjectManager(connector)
        member = objects.Member(connector, name='member1', ip='some-ip')

        ibom.restart_all_services(member)

        connector.call_func.assert_called_once_with(
            'restartservices', mock.ANY, mock.ANY)

    def test_update_network_updates_object(self):
        ref = 'infoblox_object_id'
        opts = 'infoblox_options'

        connector = mock.Mock()
        ib_network = objects.Network(connector,
                                     _ref=ref, options=opts)
        ibom = om.InfobloxObjectManager(connector)
        ibom.update_network_options(ib_network)

        connector.update_object.assert_called_once_with(ref, {'options': opts},
                                                        mock.ANY)

    def test_update_network_updates_eas_if_not_null(self):
        ref = 'infoblox_object_id'
        opts = 'infoblox_options'
        eas = 'some-eas'

        connector = mock.Mock()
        ib_network = objects.Network(connector,
                                     _ref=ref, options=opts)
        ibom = om.InfobloxObjectManager(connector)
        ibom.update_network_options(ib_network, eas)

        connector.update_object.assert_called_once_with(ref, {'options': opts,
                                                              'extattrs': eas},
                                                        mock.ANY)

    def test_create_ip_range_creates_range_object(self):
        net_view = 'net-view-name'
        start_ip = '192.168.1.1'
        end_ip = '192.168.1.123'
        disable = False

        connector = mock.Mock()
        connector.get_object.return_value = None

        ibom = om.InfobloxObjectManager(connector)
        ibom.create_ip_range(net_view, start_ip, end_ip, None, disable,
                             self.EXT_ATTRS)

        assert connector.get_object.called
        matcher = PayloadMatcher({'start_addr': start_ip,
                                  'end_addr': end_ip,
                                  'network_view': net_view,
                                  'extattrs': self.EXT_ATTRS,
                                  'disable': disable})
        connector.create_object.assert_called_once_with('range', matcher,
                                                        mock.ANY)

    def test_delete_ip_range_deletes_infoblox_object(self):
        net_view = 'net-view-name'
        start_ip = '192.168.1.1'
        end_ip = '192.168.1.123'

        connector = mock.Mock()
        connector.get_object.return_value = mock.MagicMock()

        ibom = om.InfobloxObjectManager(connector)

        ibom.delete_ip_range(net_view, start_ip, end_ip)

        matcher = PayloadMatcher({'start_addr': start_ip,
                                  'network_view': net_view})
        connector.get_object.assert_called_once_with(
            'range', matcher, extattrs=None,
            force_proxy=mock.ANY, return_fields=mock.ANY)
        connector.delete_object.assert_called_once_with(mock.ANY)

    def test_delete_network_deletes_infoblox_network(self):
        net_view = 'net-view-name'
        cidr = '192.168.1.0/24'

        connector = mock.Mock()
        connector.get_object.return_value = mock.MagicMock()

        ibom = om.InfobloxObjectManager(connector)

        ibom.delete_network(net_view, cidr)

        matcher = PayloadMatcher({'network_view': net_view,
                                  'network': cidr})
        connector.get_object.assert_called_once_with(
            'network', matcher, extattrs=None,
            force_proxy=mock.ANY, return_fields=mock.ANY)
        connector.delete_object.assert_called_once_with(mock.ANY)

    def test_delete_network_view_deletes_infoblox_object(self):
        net_view = 'net-view-name'

        connector = mock.Mock()
        connector.get_object.return_value = mock.MagicMock()

        ibom = om.InfobloxObjectManager(connector)

        ibom.delete_network_view(net_view)

        matcher = PayloadMatcher({'name': net_view})
        connector.get_object.assert_called_once_with(
            'networkview', matcher, extattrs=None,
            force_proxy=mock.ANY, return_fields=mock.ANY)
        connector.delete_object.assert_called_once_with(mock.ANY)

    def test_bind_names_updates_host_record(self):
        dns_view_name = 'dns-view-name'
        fqdn = 'host.global.com'
        ip = '192.168.1.1'
        extattrs = None

        connector = mock.Mock()
        connector.get_object.return_value = mock.MagicMock()

        ibom = om.InfobloxObjectManager(connector)

        ibom.bind_name_with_host_record(dns_view_name, ip, fqdn, extattrs)

        matcher = PayloadMatcher({'view': dns_view_name,
                                  PayloadMatcher.ANYKEY: ip})
        connector.get_object.assert_called_once_with(
            'record:host', matcher, extattrs=None,
            force_proxy=mock.ANY, return_fields=mock.ANY)

        matcher = PayloadMatcher({'name': fqdn})
        connector.update_object.assert_called_once_with(mock.ANY, matcher,
                                                        mock.ANY)

    def test_bind_names_with_a_record(self):
        dns_view_name = 'dns-view-name'
        name = 'host1'
        ip = '192.168.1.1'
        extattrs = None
        bind_list = ['record:a', 'record:aaaa', 'record:ptr']

        connector = mock.Mock()
        connector.get_object.return_value = None

        ibom = om.InfobloxObjectManager(connector)
        ibom.bind_name_with_record_a(dns_view_name, ip, name,
                                     bind_list, extattrs)

        exp_for_a = {'view': dns_view_name,
                     'ipv4addr': ip}
        exp_for_ptr = {'view': dns_view_name,
                       'ipv4addr': ip}
        calls = [mock.call('record:a', exp_for_a, return_fields=mock.ANY),
                 mock.call('record:ptr', exp_for_ptr, return_fields=mock.ANY)]
        connector.get_object.assert_has_calls(calls)

        exp_for_a['name'] = name
        exp_for_ptr['ptrdname'] = name

        create_calls = [mock.call('record:a', exp_for_a, mock.ANY),
                        mock.call('record:ptr', exp_for_ptr, mock.ANY)]
        connector.create_object.assert_has_calls(create_calls)

    def test_create_dns_view_creates_view_object(self):
        net_view_name = 'net-view-name'
        dns_view_name = 'dns-view-name'

        connector = mock.Mock()
        connector.get_object.return_value = None

        ibom = om.InfobloxObjectManager(connector)

        ibom.create_dns_view(net_view_name, dns_view_name)

        matcher = PayloadMatcher({'name': dns_view_name,
                                  'network_view': net_view_name})
        connector.get_object.assert_called_once_with(
            'view', matcher, return_fields=mock.ANY)
        connector.create_object.assert_called_once_with(
            'view', matcher, mock.ANY)

    def test_default_net_view_is_never_deleted(self):
        connector = mock.Mock()

        ibom = om.InfobloxObjectManager(connector)

        ibom.delete_network_view('default')

        assert not connector.delete_object.called

    def test_has_networks(self):
        connector = mock.Mock()
        connector.get_object.return_value = None
        ibom = om.InfobloxObjectManager(connector)
        net_view_name = 'some-view'

        result = ibom.has_networks(net_view_name)

        matcher = PayloadMatcher({'network_view': net_view_name})
        connector.get_object.assert_called_once_with(
            'network', matcher, return_fields=mock.ANY,
            force_proxy=mock.ANY, extattrs=None)
        self.assertEqual(False, result)

    def test_network_exists(self):
        connector = mock.Mock()
        connector.get_object.return_value = None
        ibom = om.InfobloxObjectManager(connector)
        net_view_name = 'some-view'
        cidr = '192.168.1.0/24'

        result = ibom.network_exists(net_view_name, cidr)

        matcher = PayloadMatcher({'network_view': net_view_name,
                                  'network': cidr})
        connector.get_object.assert_called_once_with(
            'network', matcher, return_fields=mock.ANY,
            force_proxy=mock.ANY, extattrs=None)
        self.assertEqual(False, result)

    def test_create_fixed_address_for_given_ip(self):
        network_view = 'test_network_view'
        ip = '192.168.0.1'
        mac = 'aa:bb:cc:dd:ee:ff'

        exp_payload = {'network_view': network_view,
                       'extattrs': self.EXT_ATTRS,
                       'ipv4addr': ip,
                       'mac': mac}

        connector = mock.Mock()
        connector.create_object.return_value = exp_payload

        ibom = om.InfobloxObjectManager(connector)
        ibom.create_fixed_address_for_given_ip(network_view, mac,
                                               ip, self.EXT_ATTRS)

        connector.create_object.assert_called_once_with('fixedaddress',
                                                        exp_payload,
                                                        mock.ANY)

    def test_create_fixed_address_from_range(self):
        network_view = 'test_network_view'
        first_ip = '192.168.0.2'
        last_ip = '192.168.0.20'
        mac = 'aa:bb:cc:dd:ee:ff'

        result = {'network_view': network_view,
                  'extattrs': self.EXT_ATTRS,
                  'ipv4addr': '192.168.0.12',
                  'mac': mac}

        connector = mock.Mock()
        connector.create_object.return_value = result

        ibom = om.InfobloxObjectManager(connector)
        ibom.create_fixed_address_from_range(network_view, mac, first_ip,
                                             last_ip, self.EXT_ATTRS)

        next_ip = (
            'func:nextavailableip:192.168.0.2-192.168.0.20,test_network_view')
        exp_payload = result.copy()
        exp_payload['ipv4addr'] = next_ip

        connector.create_object.assert_called_once_with('fixedaddress',
                                                        exp_payload,
                                                        mock.ANY)

    def test_create_fixed_address_from_cidr(self):
        network_view = 'test_network_view'
        cidr = '192.168.0.0/24'
        mac = 'aa:bb:cc:dd:ee:ff'

        result = {'network_view': network_view,
                  'extattrs': self.EXT_ATTRS,
                  'ipv4addr': '192.168.0.12',
                  'mac': mac}

        connector = mock.Mock()
        connector.create_object.return_value = result

        ibom = om.InfobloxObjectManager(connector)
        ibom.create_fixed_address_from_cidr(network_view, mac, cidr,
                                            self.EXT_ATTRS)

        next_ip = 'func:nextavailableip:192.168.0.0/24,test_network_view'
        exp_payload = result.copy()
        exp_payload['ipv4addr'] = next_ip

        connector.create_object.assert_called_once_with('fixedaddress',
                                                        exp_payload,
                                                        mock.ANY)

    def test_delete_fixed_address(self):
        network_view = 'test_network_view'
        ip = '192.168.0.25'

        connector = mock.Mock()
        connector.get_object.return_value = mock.MagicMock()

        ibom = om.InfobloxObjectManager(connector)
        ibom.delete_fixed_address(network_view, ip)

        payload = {'network_view': network_view,
                   'ipv4addr': ip}
        connector.get_object.assert_called_once_with(
            'fixedaddress', payload, extattrs=None,
            return_fields=mock.ANY, force_proxy=mock.ANY)
        connector.delete_object.assert_called_once_with(mock.ANY)

    def test_member_is_assigned_as_list_on_network_create(self):
        net_view = 'net-view-name'
        cidr = '192.168.1.0/24'
        nameservers = []
        members = [
            objects.AnyMember(name='just-a-single-member-ip',
                              ip='192.168.1.25',
                              _struct='dhcpmember')
        ]
        gateway_ip = '192.168.1.1'
        dhcp_trel_ip = '8.8.8.8'
        extattrs = None
        expected_payload = {
            'members': [{'ipv4addr': '192.168.1.25',
                         '_struct': 'dhcpmember',
                         'name': 'just-a-single-member-ip'}],
            'network_view': net_view,
            'network': cidr,
            'options': [{'name': 'routers', 'value': gateway_ip},
                        {'name': 'dhcp-server-identifier',
                         'value': dhcp_trel_ip,
                         'num': 54}]}

        connector = mock.Mock()
        ibom = om.InfobloxObjectManager(connector)

        ibom.create_network(net_view, cidr, nameservers, members, gateway_ip,
                            dhcp_trel_ip, extattrs)

        assert not connector.get_object.called
        connector.create_object.assert_called_once_with('network',
                                                        expected_payload,
                                                        mock.ANY)

    def test_create_dns_zone_with_grid_secondaries(self):
        dns_view_name = 'dns-view-name'
        fqdn = 'host.global.com'
        primary_dns_members = [objects.AnyMember(name='member_primary',
                                                 _struct='memberserver')]
        secondary_dns_members = [objects.AnyMember(name='member_secondary',
                                                   _struct='memberserver')]
        zone_format = 'IPV4'

        connector = mock.Mock()
        connector.get_object.return_value = None

        ibom = om.InfobloxObjectManager(connector)

        zone = ibom.create_dns_zone(dns_view_name, fqdn, primary_dns_members,
                                    secondary_dns_members,
                                    zone_format=zone_format)

        matcher = PayloadMatcher({'view': dns_view_name,
                                  'fqdn': fqdn})
        connector.get_object.assert_called_once_with('zone_auth', matcher,
                                                     return_fields=mock.ANY)

        payload = {'view': dns_view_name,
                   'fqdn': fqdn,
                   'zone_format': zone_format,
                   'grid_primary': [{'name': primary_dns_members[0].name,
                                     '_struct': 'memberserver'}],
                   'grid_secondaries': [{'name': member.name,
                                         '_struct': 'memberserver'}
                                        for member in secondary_dns_members]
                   }
        connector.create_object.assert_called_once_with('zone_auth', payload,
                                                        mock.ANY)
        self.assertIsInstance(zone, objects.DNSZone)

    def test_create_dns_zone_creates_zone_auth_object(self):
        dns_view_name = 'dns-view-name'
        fqdn = 'host.global.com'
        member = objects.AnyMember(name='member_name', ip='192.168.1.2',
                                   _struct='memberserver')
        zone_format = 'IPV4'

        connector = mock.Mock()
        connector.get_object.return_value = None

        ibom = om.InfobloxObjectManager(connector)

        ibom.create_dns_zone(dns_view_name, fqdn, [member],
                             zone_format=zone_format)

        matcher = PayloadMatcher({'view': dns_view_name,
                                  'fqdn': fqdn})
        connector.get_object.assert_called_once_with('zone_auth', matcher,
                                                     return_fields=mock.ANY)

        matcher = PayloadMatcher({'view': dns_view_name,
                                  'fqdn': fqdn,
                                  'zone_format': zone_format,
                                  'name': member.name})
        connector.create_object.assert_called_once_with('zone_auth', matcher,
                                                        mock.ANY)

    def test_delete_all_associated_objects(self):
        a_rec_ref = ('record:a/ZG5zLmJpbmRfYSQuNC5jb20ubXlfem9uZSxuYW'
                     '1lLDE5Mi4xNjguMS41:name.my_zone.com/my_dns_view')
        reply_map = {
            'ipv4address': [{
                '_ref': ('ipv4address/Li5pcHY0X2FkZHJlc3MkMTky'
                         'LjE2OC4xLjEwLzE:192.168.1.10/my_view'),
                'objects': [a_rec_ref]
            }],
            a_rec_ref: {'_ref': a_rec_ref,
                        'view': 'my_dns_view',
                        'name': 'name.my_zone.com'},
        }

        def get_object(ref, *args, **kwargs):
            if ref in reply_map:
                return reply_map[ref]

        connector = mock.Mock()
        connector.get_object.side_effect = get_object
        ibom = om.InfobloxObjectManager(connector)
        delete_list = ['record:a']
        ibom.delete_all_associated_objects('some_view', '192.168.1.10',
                                           delete_list)

        payload = {'network_view': 'some_view', 'ip_address': '192.168.1.10'}
        calls = [mock.call('ipv4address', payload, extattrs=mock.ANY,
                           force_proxy=mock.ANY, return_fields=mock.ANY),
                 mock.call(a_rec_ref),
                 mock.call('record:cname', {'view': 'my_dns_view',
                                            'canonical': 'name.my_zone.com'}),
                 mock.call('record:txt', {'name': 'name.my_zone.com',
                                          'view': 'my_dns_view'})]
        connector.get_object.assert_has_calls(calls)
        connector.delete_object.assert_called_once_with(a_rec_ref)

    def test_delete_object_by_ref(self):
        """Verify that exception would not be raised for delete by reference.

        """
        ref = mock.Mock()

        # Create an exception object instance with dummy error message.
        exception_kwargs = {'ref': ref, 'content': 'Not Found', 'code': 404}

        err = exceptions.InfobloxCannotDeleteObject(
            'specified object not found', **exception_kwargs)

        connector = mock.Mock()
        connector.delete_object.side_effect = err

        ibom = om.InfobloxObjectManager(connector)
        ibom.delete_object_by_ref(ref)
        connector.delete_object.assert_called_once_with(ref)
