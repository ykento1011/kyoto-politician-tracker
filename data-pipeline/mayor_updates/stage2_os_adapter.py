"""Disabled Windows ports for Stage 2; admin authority stays in local PS5.1.

No elevation, shell, service, task or network is started at import/initialization.
The already open administrator consoles run the broker and independent guardian.
Only a private, separately re-pinned copy can enable LIVE_OS_ADAPTER_ENABLED.
"""
from copy import deepcopy
from hashlib import sha256
from ipaddress import ip_address
import json
import os
from pathlib import Path
import re
import socket
import struct
import time


from .projection import Hold
from .stage2_guard import _record
from .stage2_acceptance import CONNECTION, PACKET, TARGETS, PROBES, require, identity

LIVE_OS_ADAPTER_ENABLED = False
OPS = frozenset(('preflight', 'read_audit', 'set_failure', 'log_boundary',
                 'export_security', 'apply_rules', 'read_denials', 'dns_evidence',
                 'confirm_exit', 'restore_rules', 'audit_unchanged', 'finish'))
MAX_WIRE = 2 * 1024 * 1024
FILETIME_EPOCH = 116444736000000000


def ticks():
    return FILETIME_EPOCH + time.time_ns() // 100


def read_json(path, limit=MAX_WIRE):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result
    with Path(path).open('rb') as stream:
        body = stream.read(limit+1)
    require(len(body) <= limit, 'IPC size limit')
    return json.loads(body.decode('utf-8-sig'), object_pairs_hook=unique)


class Mailbox:
    """Exclusive local file IPC, not a TCP/pipe endpoint or command interpreter.

    check_path holds and validates owner-only/non-reparse paths. check_peer
    validates the broker's actual retained process/token/image, not its JSON claim.
    A sequence is consumed before publication. Timeouts never replay operations.
    """
    def __init__(self, root, binding, check_path, check_peer, *, clock=time.monotonic,
                 sleep=time.sleep):
        self.root = Path(root)
        self.binding = deepcopy(binding)
        require(set(binding) == {'run_id', 'runtime_sha256', 'plan_sha256', 'nonce'}, 'IPC binding keys')
        require(re.fullmatch('[0-9a-f]{32}', binding['run_id']) and
                all(re.fullmatch('[0-9a-f]{64}', binding[k]) for k in binding if k != 'run_id'),
                'IPC binding values')
        self.check_path, self.check_peer = check_path, check_peer
        self.clock, self.sleep, self.seq = clock, sleep, 0
        self.check_path(self.root)

    def call(self, operation, payload=None, *, deadline=None):
        require(operation in OPS, 'Unknown privileged operation')
        require(not (self.root/'STOP.json').exists(), 'Independent local STOP')
        self.check_path(self.root/'agent_ready.json')
        peer = read_json(self.root/'agent_ready.json', 16384)
        require(peer.get('binding') == self.binding, 'Admin peer binding')
        self.check_peer(peer['identity'], elevated=True)
        self.seq += 1
        request = {'binding': self.binding, 'sequence': self.seq, 'operation': operation,
                   'payload': payload or {}}
        require(len(json.dumps(request).encode()) <= 65536, 'Request size')
        _record(self.root, 'request-%04d.json' % self.seq, request)
        end = min(deadline, self.clock()+5) if deadline is not None else self.clock()+5
        response = self.root/('response-%04d.json' % self.seq)
        while not response.exists():
            require(not (self.root/'STOP.json').exists(), 'Independent local STOP')
            require(self.clock() < end, 'Admin IPC timeout; never retry this request')
            self.sleep(.02)
        self.check_path(response)
        result = read_json(response)
        require(result.get('binding') == self.binding and result.get('sequence') == self.seq and
                result.get('operation') == operation, 'IPC response substitution')
        require(result.get('ok') is True, 'Admin operation HOLD: '+str(result.get('error', 'unknown')))
        return result['result']

    def restore_audit_out_of_band(self):
        # The guardian does not depend on an agent request, broker responsiveness,
        # the Python deadline or the network. It sees this immutable STOP file.
        if not (self.root/'STOP.json').exists():
            _record(self.root, 'STOP.json', {'binding': self.binding, 'reason': 'audit_restore_required'})


def decode_5157(row, *, device_to_dos):
    """Trusted pinned admin parser emits XML + its exact decoded EventData.

    Parsing is performed in PS5.1/System.Xml to reuse the prepared runtime; no
    unpinned XML C extension is introduced into the fixed Python worker runtime.
    The peer/token/code-PIN boundary is verified before accepting any row.
    """
    xml=row['xml']
    require(type(xml) is str and len(xml.encode('utf-8'))<=65536 and
            '<!DOCTYPE' not in xml.upper() and '<!ENTITY' not in xml.upper() and
            sha256(xml.encode('utf-8')).hexdigest()==row['xml_sha256'], 'Original event XML hash/size')
    require(row['event_id']==5157 and row['provider']=='Microsoft-Windows-Security-Auditing' and
            type(row['record_id']) is int and type(row['utc_tick']) is int, 'Security event type')
    fields=row['fields'];owner=row['owner']
    pid=int(fields['ProcessID'],0) if fields['ProcessID'].startswith('0x') else int(fields['ProcessID'])
    who=identity(owner)
    require(who['pid']==pid and device_to_dos(fields['Application']).casefold()==who['image'].casefold(),
            '5157 payload PID/image differs from retained process')
    return {'record_id':row['record_id'],'event_id':5157,'utc_tick':row['utc_tick'],
            'payload_pid':pid,'application':fields['Application'],'owner':deepcopy(owner),
            'tuple':[str(ip_address(fields['SourceAddress'])),int(fields['SourcePort']),
                     str(ip_address(fields['DestAddress'])),int(fields['DestPort']),int(fields['Protocol'])],
            'filter_id':int(fields['FilterRTID']),'layer_id':int(fields['LayerRTID']),
            'direction':'Outbound' if fields['Direction']=='%%14593' else 'Inbound'
                        if fields['Direction']=='%%14592' else 'UNKNOWN',
            'xml':xml,'xml_sha256':row['xml_sha256'],'raw_fields':fields}

class FixedProbes:
    """Only fixed sockets; no HTTP, hostname resolution, fallback or retry."""
    def __init__(self, capture_actor, dns_query, *, socket_factory=socket.socket,
                 now=ticks, monotonic=time.monotonic):
        self.capture_actor, self.dns_query = capture_actor, dns_query
        self.socket_factory, self.now, self.monotonic = socket_factory, now, monotonic
        self.used = set()

    def run(self, name, blocked, rid, resolvers, deadline):
        key = (name, blocked)
        require(name in PROBES and key not in self.used and len(self.used) < 9 and
                not (name == 'system_dns_proxy' and not blocked), 'Probe already consumed/not approved')
        self.used.add(key)  # failures consume the attempt
        actor = self.capture_actor()
        require(actor['sid'].endswith('-1004'), 'Probe actor SID')
        result = {'run_id': rid, 'probe_id': name, 'blocked': blocked, 'actor': actor,
                  'client_calls': 1, 'retries': 0, 'http_requests': 0, 'start_tick': self.now()}
        left = min(1., deadline-self.monotonic())
        require(left > 0, 'Probe deadline expired')
        if name == 'system_dns_proxy':
            result.update(self.dns_query('stage2-'+rid+'.example.com.', left))
            result.update(query='stage2-'+rid+'.example.com.', resolvers=resolvers)
            result['end_tick'] = self.now()
            return result
        address, port, protocol = TARGETS[name]
        family = socket.AF_INET6 if ip_address(address).version == 6 else socket.AF_INET
        kind = socket.SOCK_STREAM if protocol == 6 else socket.SOCK_DGRAM
        with self.socket_factory(family, kind, protocol) as sock:
            sock.settimeout(left)
            # Assign a real local port without choosing another remote target.
            sock.bind(('::' if family == socket.AF_INET6 else '0.0.0.0', 0))
            accepted = False
            response = False
            try:
                if protocol == 6:
                    sock.connect((address, port)); accepted = response = True
                else:
                    # One DNS datagram. Transaction ID and question must match
                    # before a reply counts as baseline reachability.
                    question = b'\x07example\x03com\x00'+struct.pack('!HH', 28 if family == socket.AF_INET6 else 1, 1)
                    packet = b'\x53\x32\x01\x00\x00\x01'+b'\x00'*6+question
                    sock.sendto(packet, (address, port)); accepted = True
                    reply, source = sock.recvfrom(4096)
                    response = (str(ip_address(source[0])) == address and source[1] == port and
                                len(reply) >= 12+len(question) and reply[:2] == b'\x53\x32' and
                                bool(reply[2] & 128) and reply[12:12+len(question)] == question)
            except (OSError, TimeoutError) as exc:
                result['socket_error'] = type(exc).__name__
            local = sock.getsockname()
            # A wildcard local address is not the observed route. The broker
            # must replace it only from a unique matching payload PID/port deny.
            result.update(target=list(TARGETS[name]), tuple=[local[0], local[1], address, port, protocol],
                          reachable=response, external_egress=(accepted if protocol == 6 else response),
                          send_accepted=accepted)
        result['end_tick'] = self.now()
        return result


class WindowsPorts:
    simulation_only = False

    def __init__(self, rpc, probes, plan, check_peer, device_to_dos, *, clock=time.monotonic):
        self.rpc, self.probes, self.plan = rpc, probes, plan
        self.check_peer, self.device_to_dos, self.clock = check_peer, device_to_dos, clock
        self.receipts, self.cached, self.filter_map = {}, {}, {}
        self.dns = None
        self.resolvers = None

    def preflight(self, plan):
        require(plan == self.plan, 'Runtime plan substitution')
        value = self.rpc.call('preflight')
        self.check_peer(value['guardian'], elevated=True)
        self.dns = value['dns']
        self.resolvers = value['resolvers']
        return value

    def read_audit(self): return self.rpc.call('read_audit')

    def set_failure(self, guid, value, *, deadline):
        require(guid == CONNECTION and type(value) is bool, 'Only 5157 failure bit')
        try:
            return self.rpc.call('set_failure', {'guid': guid, 'value': value}, deadline=deadline)
        except BaseException:
            # Never re-enable or retry a consumed operation through the broker.
            # The independent guardian gets a separate immutable stop signal.
            self.rpc.restore_audit_out_of_band()
            raise

    def log_boundary(self): return self.rpc.call('log_boundary')
    def export_security(self, phase, rid):
        require(rid == self.plan['run_id'] and phase in ('before', 'after'), 'Export binding')
        return self.rpc.call('export_security', {'phase': phase})

    def apply_and_verify_rules(self, rules, *, deadline):
        prefix = 'GikaiMikata-Stage2-'+self.plan['run_id']+'-'
        require(rules == [prefix+'Inbound', prefix+'Outbound'], 'Exact two rules only')
        rows = self.rpc.call('apply_rules', {}, deadline=deadline)
        mapping = {}
        for row in rows:
            require(type(row['id']) is int and row['id'] > 0 and row['id'] not in mapping and
                    row['rule'] in rules and row['origin'] == row['rule'] and
                    row['snapshot_unchanged'] is True, 'WFP filter origin not proven')
            mapping[row['id']] = row['rule']
        require(set(mapping.values()) == set(rules), 'Missing rule/filter binding')
        self.filter_map = mapping
        return mapping

    def probe(self, name, *, blocked, run_id, deadline):
        require(run_id == self.plan['run_id'], 'Probe run')
        value = self.probes.run(name, blocked, run_id, self.resolvers, deadline)
        if blocked:
            raw = self.rpc.call('read_denials', {'after': 0, 'limit': 64}, deadline=deadline)
            require(raw.get('truncated') is False and raw.get('lost')==0,'Probe evidence cap/loss')
            normalized = self._normalize(raw['events'])
            candidates = [e for e in normalized if self._match(value, e)]
            if name == 'system_dns_proxy':
                evidence = self.rpc.call('dns_evidence', {'receipt': value}, deadline=deadline)
                value.update(evidence)
                # A unique service denial must supply the actual local endpoint;
                # never invent a service socket from the requesting process.
                candidates = [e for e in normalized if self._match(value, e, dns=True)]
            require(len(candidates) == 1, 'Missing/ambiguous OS denial')
            value['tuple'] = candidates[0]['tuple']
            # A successful TCP connect/reply is egress. A failed call alone is
            # insufficient, but unique observed WFP denial proves this blocked attempt.
            require(value.get('external_egress') is False, 'Observed external response')
            self.receipts[name] = deepcopy(value)
        return value

    def _match(self, receipt, event, dns=False):
        if not receipt['start_tick'] <= event['utc_tick'] <= receipt['end_tick']:
            return False
        if dns or receipt['probe_id'] == 'system_dns_proxy':
            return (identity(event['owner']) == identity(self.dns) and event['tuple'][3:] == [53, 17] and
                    event['tuple'][2] in receipt.get('resolvers', []) and
                    receipt.get('query_complete') is True and receipt.get('service_send_count_verified') is True)
        return (identity(event['owner']) == identity(receipt['actor']) and
                event['tuple'][1:] == receipt['tuple'][1:])

    def _normalize(self, rows):
        result = []
        for row in rows:
            decoded = decode_5157(row, device_to_dos=self.device_to_dos)
            require(decoded['filter_id'] in self.filter_map and
                    row['filter_origin'] == self.filter_map[decoded['filter_id']], 'Event filter changed')
            decoded['rule_name'] = self.filter_map[decoded['filter_id']]
            result.append(decoded)
        return result

    def read_denials(self, rid, *, limit, after_record, deadline):
        require(rid == self.plan['run_id'] and type(limit) is int and 0 < limit <= 64 and
                type(after_record) is int and after_record >= 0, 'Denial request binding/bound')
        batch = self.rpc.call('read_denials', {'after': after_record, 'limit': limit}, deadline=deadline)
        events = self._normalize(batch['events'])
        for event in events:
            names = [name for name, receipt in self.receipts.items() if self._match(receipt, event)]
            require(len(names) == 1, 'Denial cannot be uniquely assigned to a fixed probe')
            name = names[0]
            event.update(run_id=rid, probe_id=name)
            if name == 'system_dns_proxy': event['query'] = self.receipts[name]['query']
        return {**batch, 'events': events}

    def confirm_local_exit(self, rid, result, *, deadline):
        return self.rpc.call('confirm_exit', {'completion': result}, deadline=deadline)

    def restore_exact_rules_by_operator(self, rules, *, deadline):
        return self.rpc.call('restore_rules', {}, deadline=deadline)

    def audit_other_settings_unchanged(self): return self.rpc.call('audit_unchanged') is True

    def stop_and_confirm_job(self):
        # No blind PID killing or unrelated Job handles. Existing native flow
        # performs its own cleanup and leaves a capability-bound journal.
        try:
            from .stage2_acceptance import WorkerFlow
            result = WorkerFlow.completion(self.plan['native_root'])
            return result['termination_confirmed'] is True
        except (Hold, OSError, ValueError, KeyError):
            return False
