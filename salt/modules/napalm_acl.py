# -*- coding: utf-8 -*-
'''
NAPALM ACL
==========

Generate and load ACL (firewall) configuration on network devices.

.. versionadded:: 2017.7.0

:codeauthor: Mircea Ulinic <ping@mirceaulinic.net>
:maturity:   new
:depends:    capirca, napalm
:platform:   unix

Dependencies
------------

The firewall configuration is generated by Capirca_.

.. _Capirca: https://github.com/google/capirca

To install Capirca, execute: ``pip install capirca``.

To be able to load configuration on network devices,
it requires NAPALM_ library to be installed:  ``pip install napalm``.
Please check Installation_ for complete details.

.. _NAPALM: https://napalm.readthedocs.io
.. _Installation: https://napalm.readthedocs.io/en/latest/installation.html
'''
from __future__ import absolute_import

import logging
log = logging.getLogger(__file__)

# Import third party libs
try:
    # pylint: disable=W0611
    import capirca
    import capirca.aclgen
    import capirca.lib.policy
    import capirca.lib.aclgenerator
    HAS_CAPIRCA = True
    # pylint: enable=W0611
except ImportError:
    HAS_CAPIRCA = False

try:
    # pylint: disable=W0611
    import napalm_base
    # pylint: enable=W0611
    HAS_NAPALM = True
except ImportError:
    HAS_NAPALM = False

# import Salt modules
from salt.utils.napalm import proxy_napalm_wrap

# ------------------------------------------------------------------------------
# module properties
# ------------------------------------------------------------------------------

__virtualname__ = 'netacl'
__proxyenabled__ = ['napalm']
# allow napalm proxy only

# ------------------------------------------------------------------------------
# property functions
# ------------------------------------------------------------------------------


def __virtual__():
    '''
    This module requires both NAPALM and Capirca.
    '''
    if HAS_CAPIRCA and HAS_NAPALM:
        return __virtualname__
    else:
        return (False, 'The netacl (napalm_acl) module cannot be loaded: \
                Please install capirca and napalm.')

# ------------------------------------------------------------------------------
# helper functions -- will not be exported
# ------------------------------------------------------------------------------


def _get_capirca_platform():  # pylint: disable=too-many-return-statements
    '''
    Given the following NAPALM grains, we can determine the Capirca platform name:

    - vendor
    - device model
    - operating system

    Not the most optimal.
    '''
    vendor = __grains__['vendor'].lower()
    os_ = __grains__['os'].lower()
    model = __grains__['model'].lower()
    if vendor == 'juniper' and 'srx' in model:
        return 'junipersrx'
    elif vendor == 'cisco' and os_ == 'ios':
        return 'cisco'
    elif vendor == 'cisco' and os_ == 'iosxr':
        return 'ciscoxr'
    elif vendor == 'cisco' and os_ == 'asa':
        return 'ciscoasa'
    elif os_ == 'linux':
        return 'iptables'
    elif vendor == 'palo alto networks':
        return 'paloaltofw'
    # anything else will point to the vendor
    # i.e.: some of the Capirca platforms are named by the device vendor
    # e.g.: eOS => arista, junos => juniper, etc.
    return vendor

# ------------------------------------------------------------------------------
# callable functions
# ------------------------------------------------------------------------------


@proxy_napalm_wrap
def load_term_config(filter_name,
                     term_name,
                     filter_options=None,
                     pillar_key='acl',
                     pillarenv=None,
                     saltenv=None,
                     merge_pillar=True,
                     revision_id=None,
                     revision_no=None,
                     revision_date=True,
                     revision_date_format='%Y/%m/%d',
                     test=False,
                     commit=True,
                     debug=False,
                     source_service=None,
                     destination_service=None,
                     **term_fields):
    '''
    Generate and load the configuration of a policy term.

    filter_name
        The name of the policy filter.

    term_name
        The name of the term.

    filter_options
        Additional filter options. These options are platform-specific.
        See the complete list of options_.

        .. _options: https://github.com/google/capirca/wiki/Policy-format#header-section

    pillar_key: ``acl``
        The key in the pillar containing the default attributes values. Default: ``acl``.
        If the pillar contains the following structure:

        .. code-block:: yaml

            firewall:
              - my-filter:
                  terms:
                    - my-term:
                        source_port: 1234
                        source_address:
                            - 1.2.3.4/32
                            - 5.6.7.8/32

        The ``pillar_key`` field would be specified as ``firewall``.

    pillarenv
        Query the master to generate fresh pillar data on the fly,
        specifically from the requested pillar environment.

    saltenv
        Included only for compatibility with
        :conf_minion:`pillarenv_from_saltenv`, and is otherwise ignored.

    merge_pillar: ``True``
        Merge the CLI variables with the pillar. Default: ``True``.

        The properties specified through the CLI have higher priority than the pillar.

    revision_id
        Add a comment in the term config having the description for the changes applied.

    revision_no
        The revision count.

    revision_date: ``True``
        Boolean flag: display the date when the term configuration was generated. Default: ``True``.

    revision_date_format: ``%Y/%m/%d``
        The date format to be used when generating the perforce data. Default: ``%Y/%m/%d`` (<year>/<month>/<day>).

    test: ``False``
        Dry run? If set as ``True``, will apply the config, discard and return the changes.
        Default: ``False`` and will commit the changes on the device.

    commit: ``True``
        Commit? Default: ``True``.

    debug: ``False``
        Debug mode. Will insert a new key under the output dictionary,
        as ``loaded_config`` containing the raw configuration loaded on the device.

    source_service
        A special service to choose from. This is a helper so the user is able to
        select a source just using the name, instead of specifying a source_port and protocol.

        As this module is available on Unix platforms only,
        it reads the IANA_ port assignment from /etc/services.

        If the user requires additional shortcuts to be referenced, they can add entries under /etc/services,
        which can be managed using the :mod:`file state <salt.states.file>`.

        .. _IANA: http://www.iana.org/assignments/port-numbers

    destination_service
        A special service to choose from. This is a helper so the user is able to
        select a source just using the name, instead of specifying a destination_port and protocol.
        Allows the same options as ``source_service``.

    term_fields
        Term attributes. To see what fields are supported, please consult the
        list of supported keywords_. Some platforms have a few other optional_
        keywords.

        .. _keywords: https://github.com/google/capirca/wiki/Policy-format#keywords
        .. _optional: https://github.com/google/capirca/wiki/Policy-format#optionally-supported-keywords

    .. note::
        The following fields are accepted (some being platform-specific):

        - action
        - address
        - address_exclude
        - comment
        - counter
        - expiration
        - destination_address
        - destination_address_exclude
        - destination_port
        - destination_prefix
        - forwarding_class
        - forwarding_class_except
        - logging
        - log_name
        - loss_priority
        - option
        - policer
        - port
        - precedence
        - principals
        - protocol
        - protocol_except
        - qos
        - pan_application
        - routing_instance
        - source_address
        - source_address_exclude
        - source_port
        - source_prefix
        - verbatim
        - packet_length
        - fragment_offset
        - hop_limit
        - icmp_type
        - ether_type
        - traffic_class_count
        - traffic_type
        - translated
        - dscp_set
        - dscp_match
        - dscp_except
        - next_ip
        - flexible_match_range
        - source_prefix_except
        - destination_prefix_except
        - vpn
        - source_tag
        - destination_tag
        - source_interface
        - destination_interface
        - flattened
        - flattened_addr
        - flattened_saddr
        - flattened_daddr
        - priority

    .. note::
        The following fields can be also a single value and a list of values:

        - action
        - address
        - address_exclude
        - comment
        - destination_address
        - destination_address_exclude
        - destination_port
        - destination_prefix
        - forwarding_class
        - forwarding_class_except
        - logging
        - option
        - port
        - precedence
        - principals
        - protocol
        - protocol_except
        - pan_application
        - source_address
        - source_address_exclude
        - source_port
        - source_prefix
        - verbatim
        - icmp_type
        - ether_type
        - traffic_type
        - dscp_match
        - dscp_except
        - flexible_match_range
        - source_prefix_except
        - destination_prefix_except
        - source_tag
        - destination_tag
        - source_service
        - destination_service

        Example: ``destination_address`` can be either defined as:

        .. code-block:: yaml

            destination_address: 172.17.17.1/24

        or as a list of destination IP addresses:

        .. code-block:: yaml

            destination_address:
                - 172.17.17.1/24
                - 172.17.19.1/24

        or a list of services to be matched:

        .. code-block:: yaml

            source_service:
                - ntp
                - snmp
                - ldap
                - bgpd

    .. note::
        The port fields ``source_port`` and ``destination_port`` can be used as above to select either
        a single value, either a list of values, but also they can select port ranges. Example:

        .. code-block:: yaml

            source_port:
                - - 1000
                  - 2000
                - - 3000
                  - 4000

        With the configuration above, the user is able to select the 1000-2000 and 3000-4000 source port ranges.

    The output is a dictionary having the same form as :mod:`net.load_config <salt.modules.napalm_network.load_config>`.

    CLI Example:

    .. code-block:: bash

        salt 'edge01.bjm01' netacl.load_term_config filter-name term-name source_address=1.2.3.4 destination_address=5.6.7.8 action=accept test=True debug=True

    Output Example:

    .. code-block:: jinja

        edge01.bjm01:
            ----------
            already_configured:
                False
            comment:
                Configuration discarded.
            diff:
                [edit firewall]
                +    family inet {
                +        /*
                +         ** $Date: 2017/03/22 $
                +         **
                +         */
                +        filter filter-name {
                +            interface-specific;
                +            term term-name {
                +                from {
                +                    source-address {
                +                        1.2.3.4/32;
                +                    }
                +                    destination-address {
                +                        5.6.7.8/32;
                +                    }
                +                }
                +                then accept;
                +            }
                +        }
                +    }
            loaded_config:
                firewall {
                    family inet {
                        replace:
                        /*
                        ** $Date: 2017/03/22 $
                        **
                        */
                        filter filter-name {
                            interface-specific;
                            term term-name {
                                from {
                                    source-address {
                                        1.2.3.4/32;
                                    }
                                    destination-address {
                                        5.6.7.8/32;
                                    }
                                }
                                then accept;
                            }
                        }
                    }
                }
            result:
                True
    '''
    if not filter_options:
        filter_options = []
    platform = _get_capirca_platform()
    term_config = __salt__['capirca.get_term_config'](platform,
                                                      filter_name,
                                                      term_name,
                                                      filter_options=filter_options,
                                                      pillar_key=pillar_key,
                                                      pillarenv=pillarenv,
                                                      saltenv=saltenv,
                                                      merge_pillar=merge_pillar,
                                                      revision_id=revision_id,
                                                      revision_no=revision_no,
                                                      revision_date=revision_date,
                                                      revision_date_format=revision_date_format,
                                                      source_service=source_service,
                                                      destination_service=destination_service,
                                                      **term_fields)
    return __salt__['net.load_config'](text=term_config,
                                       test=test,
                                       commit=commit,
                                       debug=debug,
                                       inherit_napalm_device=napalm_device)  # pylint: disable=undefined-variable


@proxy_napalm_wrap
def load_filter_config(filter_name,
                       filter_options=None,
                       terms=None,
                       prepend=True,
                       pillar_key='acl',
                       pillarenv=None,
                       saltenv=None,
                       merge_pillar=True,
                       only_lower_merge=False,
                       revision_id=None,
                       revision_no=None,
                       revision_date=True,
                       revision_date_format='%Y/%m/%d',
                       test=False,
                       commit=True,
                       debug=False,
                       **kwargs):  # pylint: disable=unused-argument
    '''
    Generate and load the configuration of a policy filter.

    .. note::

        The order of the terms is very important. The configuration loaded
        on the device respects the order defined in the ``terms`` and/or
        inside the pillar.

        When merging the ``terms`` with the pillar data, consider the
        ``prepend`` argument to make sure the order is correct!

    filter_name
        The name of the policy filter.

    filter_options
        Additional filter options. These options are platform-specific.
        See the complete list of options_.

        .. _options: https://github.com/google/capirca/wiki/Policy-format#header-section

    terms
        List of terms for this policy filter.
        If not specified or empty, will try to load the configuration from the pillar,
        unless ``merge_pillar`` is set as ``False``.

    prepend: ``True``
        When ``merge_pillar`` is set as ``True``, the final list of terms generated by merging
        the terms from ``terms`` with those defined in the pillar (if any): new terms are prepended
        at the beginning, while existing ones will preserve the position. To add the new terms
        at the end of the list, set this argument to ``False``.

    pillar_key: ``acl``
        The key in the pillar containing the default attributes values. Default: ``acl``.

    pillarenv
        Query the master to generate fresh pillar data on the fly,
        specifically from the requested pillar environment.

    saltenv
        Included only for compatibility with
        :conf_minion:`pillarenv_from_saltenv`, and is otherwise ignored.

    merge_pillar: ``True``
        Merge the CLI variables with the pillar. Default: ``True``.

        The merge logic depends on the ``prepend`` argument and
        the CLI has higher priority than the pillar.

    only_lower_merge: ``False``
        Specify if it should merge only the terms fields. Otherwise it will try
        to merge also filters fields. Default: ``False``.
        This option requires ``merge_pillar``, otherwise it is ignored.

    revision_id
        Add a comment in the filter config having the description for the changes applied.

    revision_no
        The revision count.

    revision_date: ``True``
        Boolean flag: display the date when the filter configuration was generated. Default: ``True``.

    revision_date_format: ``%Y/%m/%d``
        The date format to be used when generating the perforce data. Default: ``%Y/%m/%d`` (<year>/<month>/<day>).

    test: ``False``
        Dry run? If set as ``True``, will apply the config, discard and return the changes.
        Default: ``False`` and will commit the changes on the device.

    commit: ``True``
        Commit? Default: ``True``.

    debug: ``False``
        Debug mode. Will insert a new key under the output dictionary,
        as ``loaded_config`` containing the raw configuration loaded on the device.

    The output is a dictionary having the same form as :mod:`net.load_config <salt.modules.napalm_network.load_config>`.

    CLI Example:

    .. code-block:: bash

        salt 'edge01.bjm01' netacl.load_filter_config my-filter pillar_key=netacl debug=True

    Output Example:

    .. code-block:: jinja

        edge01.bjm01:
            ----------
            already_configured:
                False
            comment:
            diff:
                [edit firewall]
                +    family inet {
                +        /*
                +         ** $Date: 2017/03/22 $
                +         **
                +         */
                +        filter my-filter {
                +            interface-specific;
                +            term my-term {
                +                from {
                +                    source-port [ 1234 1235 ];
                +                }
                +                then {
                +                    reject;
                +                }
                +            }
                +            term my-other-term {
                +                from {
                +                    protocol tcp;
                +                    source-port 5678-5680;
                +                }
                +                then accept;
                +            }
                +        }
                +    }
            loaded_config:
                firewall {
                    family inet {
                        replace:
                        /*
                        ** $Date: 2017/03/22 $
                        **
                        */
                        filter my-filter {
                            interface-specific;
                            term my-term {
                                from {
                                    source-port [ 1234 1235 ];
                                }
                                then {
                                    reject;
                                }
                            }
                            term my-other-term {
                                from {
                                    protocol tcp;
                                    source-port 5678-5680;
                                }
                                then accept;
                            }
                        }
                    }
                }
            result:
                True

    The filter configuration has been loaded from the pillar, having the following structure:

    .. code-block:: yaml

        netacl:
          - my-filter:
              terms:
                - my-term:
                    source_port:
                     - 1234
                     - 1235
                    action: reject
                - my-other-term:
                    source_port:
                      - - 5678
                        - 5680
                    protocol: tcp
                    action: accept
    '''
    if not filter_options:
        filter_options = []
    if not terms:
        terms = []
    platform = _get_capirca_platform()
    filter_config = __salt__['capirca.get_filter_config'](platform,
                                                          filter_name,
                                                          terms=terms,
                                                          prepend=prepend,
                                                          filter_options=filter_options,
                                                          pillar_key=pillar_key,
                                                          pillarenv=pillarenv,
                                                          saltenv=saltenv,
                                                          merge_pillar=merge_pillar,
                                                          only_lower_merge=only_lower_merge,
                                                          revision_id=revision_id,
                                                          revision_no=revision_no,
                                                          revision_date=revision_date,
                                                          revision_date_format=revision_date_format)
    return __salt__['net.load_config'](text=filter_config,
                                       test=test,
                                       commit=commit,
                                       debug=debug,
                                       inherit_napalm_device=napalm_device)  # pylint: disable=undefined-variable


@proxy_napalm_wrap
def load_policy_config(filters=None,
                       prepend=True,
                       pillar_key='acl',
                       pillarenv=None,
                       saltenv=None,
                       merge_pillar=True,
                       only_lower_merge=False,
                       revision_id=None,
                       revision_no=None,
                       revision_date=True,
                       revision_date_format='%Y/%m/%d',
                       test=False,
                       commit=True,
                       debug=False,
                       **kwargs):  # pylint: disable=unused-argument
    '''
    Generate and load the configuration of the whole policy.

    .. note::

        The order of the filters and their terms is very important.
        The configuration loaded on the device respects the order
        defined in the ``filters`` and/or inside the pillar.

        When merging the ``filters`` with the pillar data, consider the
        ``prepend`` argument to make sure the order is correct!

    filters
        List of filters for this policy.
        If not specified or empty, will try to load the configuration from the pillar,
        unless ``merge_pillar`` is set as ``False``.

    prepend: ``True``
        When ``merge_pillar`` is set as ``True``, the final list of filters generated by merging
        the filters from ``filters`` with those defined in the pillar (if any): new filters are prepended
        at the beginning, while existing ones will preserve the position. To add the new filters
        at the end of the list, set this argument to ``False``.

    pillar_key: ``acl``
        The key in the pillar containing the default attributes values. Default: ``acl``.

    pillarenv
        Query the master to generate fresh pillar data on the fly,
        specifically from the requested pillar environment.

    saltenv
        Included only for compatibility with
        :conf_minion:`pillarenv_from_saltenv`, and is otherwise ignored.

    merge_pillar: ``True``
        Merge the CLI variables with the pillar. Default: ``True``.

        The merge logic depends on the ``prepend`` argument and
        the CLI has higher priority than the pillar.

    only_lower_merge: ``False``
        Specify if it should merge only the filters and terms fields. Otherwise it will try
        to merge everything at the policy level. Default: ``False``.
        This option requires ``merge_pillar``, otherwise it is ignored.

    revision_id
        Add a comment in the policy config having the description for the changes applied.

    revision_no
        The revision count.

    revision_date: ``True``
        Boolean flag: display the date when the policy configuration was generated. Default: ``True``.

    revision_date_format: ``%Y/%m/%d``
        The date format to be used when generating the perforce data. Default: ``%Y/%m/%d`` (<year>/<month>/<day>).

    test: ``False``
        Dry run? If set as ``True``, will apply the config, discard and return the changes.
        Default: ``False`` and will commit the changes on the device.

    commit: ``True``
        Commit? Default: ``True``.

    debug: ``False``
        Debug mode. Will insert a new key under the output dictionary,
        as ``loaded_config`` containing the raw configuration loaded on the device.

    The output is a dictionary having the same form as :mod:`net.load_config <salt.modules.napalm_network.load_config>`.

    CLI Example:

    .. code-block:: bash

        salt 'edge01.flw01' netacl.load_policy_config debug=True

    Output Example:

    .. code-block:: text

        edge01.flw01:
            ----------
            already_configured:
                False
            comment:
            diff:
                ---
                +++
                @@ -1228,9 +1228,24 @@
                 !
                +ipv4 access-list my-filter
                + 10 remark my-term
                + 20 deny tcp host 1.2.3.4 eq 1234 any
                + 30 deny udp host 1.2.3.4 eq 1234 any
                + 40 deny tcp host 1.2.3.4 eq 1235 any
                + 50 deny udp host 1.2.3.4 eq 1235 any
                + 60 remark my-other-term
                + 70 permit tcp any range 5678 5680 any
                +!
                +!
                +ipv4 access-list block-icmp
                + 10 remark first-term
                + 20 deny icmp any any
                 !
            loaded_config:
                ! $Date: 2017/03/22 $
                no ipv4 access-list my-filter
                ipv4 access-list my-filter
                 remark my-term
                 deny tcp host 1.2.3.4 eq 1234 any
                 deny udp host 1.2.3.4 eq 1234 any
                 deny tcp host 1.2.3.4 eq 1235 any
                 deny udp host 1.2.3.4 eq 1235 any
                 remark my-other-term
                 permit tcp any range 5678 5680 any
                exit
                no ipv4 access-list block-icmp
                ipv4 access-list block-icmp
                 remark first-term
                 deny icmp any any
                exit
            result:
                True

    The policy configuration has been loaded from the pillar, having the following structure:

    .. code-block:: yaml

        acl:
          - my-filter:
              terms:
                - my-term:
                    source_port:
                     - 1234
                     - 1235
                    protocol:
                      - tcp
                      - udp
                    source_address: 1.2.3.4
                    action: reject
                - my-other-term:
                    source_port:
                      - [5678, 5680]
                    protocol: tcp
                    action: accept
          - block-icmp:
              terms:
                - first-term:
                    protocol:
                      - icmp
                    action: reject
    '''
    if not filters:
        filters = []
    platform = _get_capirca_platform()
    policy_config = __salt__['capirca.get_policy_config'](platform,
                                                          filters=filters,
                                                          prepend=prepend,
                                                          pillar_key=pillar_key,
                                                          pillarenv=pillarenv,
                                                          saltenv=saltenv,
                                                          merge_pillar=merge_pillar,
                                                          only_lower_merge=only_lower_merge,
                                                          revision_id=revision_id,
                                                          revision_no=revision_no,
                                                          revision_date=revision_date,
                                                          revision_date_format=revision_date_format)
    return __salt__['net.load_config'](text=policy_config,
                                       test=test,
                                       commit=commit,
                                       debug=debug,
                                       inherit_napalm_device=napalm_device)  # pylint: disable=undefined-variable


def get_filter_pillar(filter_name,
                      pillar_key='acl',
                      pillarenv=None,
                      saltenv=None):
    '''
    Helper that can be used inside a state SLS,
    in order to get the filter configuration given its name.

    filter_name
        The name of the filter.

    pillar_key
        The root key of the whole policy config.

    pillarenv
        Query the master to generate fresh pillar data on the fly,
        specifically from the requested pillar environment.

    saltenv
        Included only for compatibility with
        :conf_minion:`pillarenv_from_saltenv`, and is otherwise ignored.
    '''
    return __salt__['capirca.get_filter_pillar'](filter_name,
                                                  pillar_key=pillar_key,
                                                  pillarenv=pillarenv,
                                                  saltenv=saltenv)


def get_term_pillar(filter_name,
                    term_name,
                    pillar_key='acl',
                    pillarenv=None,
                    saltenv=None):
    '''
    Helper that can be used inside a state SLS,
    in order to get the term configuration given its name,
    under a certain filter uniquely identified by its name.

    filter_name
        The name of the filter.

    term_name
        The name of the term.

    pillar_key: ``acl``
        The root key of the whole policy config. Default: ``acl``.

    pillarenv
        Query the master to generate fresh pillar data on the fly,
        specifically from the requested pillar environment.

    saltenv
        Included only for compatibility with
        :conf_minion:`pillarenv_from_saltenv`, and is otherwise ignored.
    '''
    return __salt__['capirca.get_term_pillar'](filter_name,
                                               term_name,
                                               pillar_key=pillar_key,
                                               pillarenv=pillarenv,
                                               saltenv=saltenv)
