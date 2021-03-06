import random
from simulation.algorithms import algorithms
from simulation.utils import popcount


# VM_TYPES = ['P',  # publisher
#             'S',  # subscriber
#             'B'   # Both
#             ]
# EVENT_TYPES = ['J',  # Join
#                'L'   # Leave
#                ]

class Event:
    def __init__(self, switch_update_count_map, switch_group_size_map, per_switch_update_count_map, num_pods,
                 num_leafs_per_pod, num_hosts_per_leaf, min_group_size, pods_algorithm, pods_rules_count_map,
                 pods_num_bitmaps, pods_num_nodes_per_bitmap, pods_redundancy_per_bitmap, pods_num_rules,
                 pods_probability, pods_node_id_width, leafs_algorithm, leafs_rules_count_map, leafs_num_bitmaps,
                 leafs_num_nodes_per_bitmap, leafs_redundancy_per_bitmap, leafs_num_rules, leafs_probability,
                 leafs_node_id_width, failed_node_type='spine', num_spines_per_pod=None, with_failures_map=None):
        self.virtual_switch_update_count_map = switch_update_count_map['virtual']
        self.leaf_switch_update_count_map = switch_update_count_map['leaf']
        self.pod_switch_update_count_map = switch_update_count_map['pod']
        self.switch_group_size_map = switch_group_size_map
        self.per_virtual_switch_update_count_map = per_switch_update_count_map['virtual']
        self.per_leaf_switch_update_count_map = per_switch_update_count_map['leaf']
        self.per_pod_switch_update_count_map = per_switch_update_count_map['pod']
        self.num_pods = num_pods
        self.num_leafs_per_pod = num_leafs_per_pod
        self.num_hosts_per_leaf = num_hosts_per_leaf
        self.num_leafs = num_pods * num_leafs_per_pod
        self.min_group_size = min_group_size
        self.pods_algorithm = pods_algorithm
        self.pods_rules_count_map = pods_rules_count_map
        self.pods_num_bitmaps = pods_num_bitmaps
        self.pods_num_nodes_per_bitmap = pods_num_nodes_per_bitmap
        self.pods_redundancy_per_bitmap = pods_redundancy_per_bitmap
        self.pods_num_rules = pods_num_rules
        self.pods_probability = pods_probability
        self.pods_node_id_width = pods_node_id_width
        self.leafs_algorithm = leafs_algorithm
        self.leafs_rules_count_map = leafs_rules_count_map
        self.leafs_num_bitmaps = leafs_num_bitmaps
        self.leafs_num_nodes_per_bitmap = leafs_num_nodes_per_bitmap
        self.leafs_redundancy_per_bitmap = leafs_redundancy_per_bitmap
        self.leafs_num_rules = leafs_num_rules
        self.leafs_probability = leafs_probability
        self.leafs_node_id_width = leafs_node_id_width
        self.failed_node_type = failed_node_type
        self.num_spines_per_pod = num_spines_per_pod
        self.with_failures_map = with_failures_map

    def _process_join_for_leafs(self, vm_host, vm_leaf, group_map, leaf_switch_update_count_map,
                                per_leaf_switch_update_count_map):
        leafs_map = group_map['leafs_map']

        leafs_with_rule = []
        for l in leafs_map:
            leaf_map = leafs_map[l]
            if 'has_rule' in leaf_map:
                leafs_with_rule += [l]
                self.leafs_rules_count_map[l] -= 1
                del leaf_map['has_rule']
            elif 'has_bitmap' in leaf_map:
                del leaf_map['has_bitmap']
            if '~bitmap' in leaf_map:
                del leaf_map['~bitmap']
        if 'leafs_default_bitmap' in group_map:
            del group_map['leafs_default_bitmap']

        if vm_leaf in leafs_map:
            leaf_map = leafs_map[vm_leaf]
            leaf_map['bitmap'] |= 1 << (vm_host % self.num_hosts_per_leaf)
        else:
            leaf_map = dict()
            leaf_map['bitmap'] = 1 << (vm_host % self.num_hosts_per_leaf)
            leafs_map[vm_leaf] = leaf_map

        algorithms.run(
            algorithm=self.leafs_algorithm,
            nodes_map=leafs_map,
            max_bitmaps=self.leafs_num_bitmaps,
            max_nodes_per_bitmap=self.leafs_num_nodes_per_bitmap,
            redundancy_per_bitmap=self.leafs_redundancy_per_bitmap,
            rules_count_map=self.leafs_rules_count_map,
            max_rules=self.leafs_num_rules,
            probability=self.leafs_probability,
            num_ports_per_node=self.num_hosts_per_leaf,
            node_id_width=self.leafs_node_id_width)

        for l in leafs_map:
            leaf_map = leafs_map[l]
            if 'has_rule' in leaf_map:
                if l not in leafs_with_rule:
                    leaf_switch_update_count_map[-1] += 1
                    per_leaf_switch_update_count_map[l] += 1
            else:
                if l in leafs_with_rule:
                    leaf_switch_update_count_map[-1] += 1
                    per_leaf_switch_update_count_map[l] += 1

        if 'has_rule' in leafs_map[vm_leaf]:
            leaf_switch_update_count_map[-1] += 1
            per_leaf_switch_update_count_map[vm_leaf] += 1

    def _process_join_for_pods(self, vm_leaf, vm_pod, group_map, pod_switch_update_count_map,
                               per_pod_switch_update_count_map):
        pods_map = group_map['pods_map']

        pods_with_rule = []
        for p in pods_map:
            pod_map = pods_map[p]
            if 'has_rule' in pod_map:
                pods_with_rule += [p]
                self.pods_rules_count_map[p] -= 1
                del pod_map['has_rule']
            elif 'has_bitmap' in pod_map:
                del pod_map['has_bitmap']
            if '~bitmap' in pod_map:
                del pod_map['~bitmap']
        if 'pods_default_bitmap' in group_map:
            del group_map['pods_default_bitmap']

        if vm_pod in pods_map:
            pod_map = pods_map[vm_pod]
            pod_map['bitmap'] |= 1 << (vm_leaf % self.num_leafs_per_pod)
        else:
            pod_map = dict()
            pod_map['bitmap'] = 1 << (vm_leaf % self.num_hosts_per_leaf)
            pods_map[vm_pod] = pod_map

        algorithms.run(
            algorithm=self.pods_algorithm,
            nodes_map=pods_map,
            max_bitmaps=self.pods_num_bitmaps,
            max_nodes_per_bitmap=self.pods_num_nodes_per_bitmap,
            redundancy_per_bitmap=self.pods_redundancy_per_bitmap,
            rules_count_map=self.pods_rules_count_map,
            max_rules=self.pods_num_rules,
            probability=self.pods_probability,
            num_ports_per_node=self.num_leafs_per_pod,
            node_id_width=self.pods_node_id_width)

        for p in pods_map:
            pod_map = pods_map[p]
            if 'has_rule' in pod_map:
                if p not in pods_with_rule:
                    pod_switch_update_count_map[-1] += 1
                    per_pod_switch_update_count_map[p] += 1
            else:
                if p in pods_with_rule:
                    pod_switch_update_count_map[-1] += 1
                    per_pod_switch_update_count_map[p] += 1

        if 'has_rule' in pods_map[vm_pod]:
            pod_switch_update_count_map[-1] += 1
            per_pod_switch_update_count_map[vm_pod] += 1

    def _process_leave_for_leafs(self, vm_host, vm_leaf, group_map, leaf_switch_update_count_map,
                                 per_leaf_switch_update_count_map):
        leafs_map = group_map['leafs_map']

        leafs_with_rule = []
        for l in leafs_map:
            leaf_map = leafs_map[l]
            if 'has_rule' in leaf_map:
                leafs_with_rule += [l]
                self.leafs_rules_count_map[l] -= 1
                del leaf_map['has_rule']
            elif 'has_bitmap' in leaf_map:
                del leaf_map['has_bitmap']
            if '~bitmap' in leaf_map:
                del leaf_map['~bitmap']
        if 'leafs_default_bitmap' in group_map:
            del group_map['leafs_default_bitmap']

        leaf_map = leafs_map[vm_leaf]
        leaf_map['bitmap'] &= ~(1 << (vm_host % self.num_hosts_per_leaf))
        if leaf_map['bitmap'] == 0:
            del leafs_map[vm_leaf]

        algorithms.run(
            algorithm=self.leafs_algorithm,
            nodes_map=leafs_map,
            max_bitmaps=self.leafs_num_bitmaps,
            max_nodes_per_bitmap=self.leafs_num_nodes_per_bitmap,
            redundancy_per_bitmap=self.leafs_redundancy_per_bitmap,
            rules_count_map=self.leafs_rules_count_map,
            max_rules=self.leafs_num_rules,
            probability=self.leafs_probability,
            num_ports_per_node=self.num_hosts_per_leaf,
            node_id_width=self.leafs_node_id_width)

        for l in leafs_map:
            leaf_map = leafs_map[l]
            if 'has_rule' in leaf_map:
                if l not in leafs_with_rule:
                    leaf_switch_update_count_map[-1] += 1
                    per_leaf_switch_update_count_map[l] += 1
            else:
                if l in leafs_with_rule:
                    leaf_switch_update_count_map[-1] += 1
                    per_leaf_switch_update_count_map[l] += 1

        if vm_leaf in leafs_map:
            if 'has_rule' in leafs_map[vm_leaf]:
                leaf_switch_update_count_map[-1] += 1
                per_leaf_switch_update_count_map[vm_leaf] += 1
        else:
            if vm_leaf in leafs_with_rule:
                leaf_switch_update_count_map[-1] += 1
                per_leaf_switch_update_count_map[vm_leaf] += 1

    def _process_leave_for_pods(self, vm_leaf, vm_pod, group_map, pod_switch_update_count_map,
                                per_pod_switch_update_count_map):
        pods_map = group_map['pods_map']

        pods_with_rule = []
        for p in pods_map:
            pod_map = pods_map[p]
            if 'has_rule' in pod_map:
                pods_with_rule += [p]
                self.pods_rules_count_map[p] -= 1
                del pod_map['has_rule']
            elif 'has_bitmap' in pod_map:
                del pod_map['has_bitmap']
            if '~bitmap' in pod_map:
                del pod_map['~bitmap']
        if 'pods_default_bitmap' in group_map:
            del group_map['pods_default_bitmap']

        pod_map = pods_map[vm_pod]
        pod_map['bitmap'] &= ~(1 << (vm_leaf % self.num_leafs_per_pod))
        if pod_map['bitmap'] == 0:
            del pods_map[vm_pod]

        algorithms.run(
            algorithm=self.pods_algorithm,
            nodes_map=pods_map,
            max_bitmaps=self.pods_num_bitmaps,
            max_nodes_per_bitmap=self.pods_num_nodes_per_bitmap,
            redundancy_per_bitmap=self.pods_redundancy_per_bitmap,
            rules_count_map=self.pods_rules_count_map,
            max_rules=self.pods_num_rules,
            probability=self.pods_probability,
            num_ports_per_node=self.num_leafs_per_pod,
            node_id_width=self.pods_node_id_width)

        for p in pods_map:
            pod_map = pods_map[p]
            if 'has_rule' in pod_map:
                if p not in pods_with_rule:
                    pod_switch_update_count_map[-1] += 1
                    per_pod_switch_update_count_map[p] += 1
            else:
                if p in pods_with_rule:
                    pod_switch_update_count_map[-1] += 1
                    per_pod_switch_update_count_map[p] += 1

        if vm_pod in pods_map:
            if 'has_rule' in pods_map[vm_pod]:
                pod_switch_update_count_map[-1] += 1
                per_pod_switch_update_count_map[vm_pod] += 1
        else:
            if vm_pod in pods_with_rule:
                pod_switch_update_count_map[-1] += 1
                per_pod_switch_update_count_map[vm_pod] += 1

    def process(self,  vm_count, vm_to_host_map, group_map):
        event_count = group_map['event_count']
        vms = group_map['vms']
        vms_types = group_map['vms_types']
        for _ in range(event_count):
            if group_map['size'] == self.min_group_size:
                event_type = 'J'
            elif group_map['size'] == vm_count:
                event_type = 'L'
            else:
                event_type = random.sample(['J', 'L'], 1)[0]

            self.virtual_switch_update_count_map[event_type] += [0]
            self.leaf_switch_update_count_map[event_type] += [0]
            self.pod_switch_update_count_map[event_type] += [0]
            virtual_switch_update_count_map = self.virtual_switch_update_count_map[event_type]
            leaf_switch_update_count_map = self.leaf_switch_update_count_map[event_type]
            pod_switch_update_count_map = self.pod_switch_update_count_map[event_type]
            switch_group_size_map = self.switch_group_size_map[event_type]

            if event_type == 'J':
                vm = random.sample(set(range(vm_count)) - set(vms), 1)[0]
                vm_host = vm_to_host_map[vm]
                vm_type = random.sample(['P', 'S', 'B'], 1)[0]
                vms += [vm]
                vms_types[vm] = vm_type
                group_map['size'] += 1
                switch_group_size_map += [group_map['size']]

                if vm_type == 'P':
                    virtual_switch_update_count_map[-1] += 1
                    self.per_virtual_switch_update_count_map[vm_host] += 1
                else:
                    vm_leaf = int(vm_host / self.num_hosts_per_leaf)
                    vm_pod = int(vm_leaf / self.num_leafs_per_pod)

                    add_leaf_to_pod = True if vm_leaf not in group_map['leafs_map'] else False
                    self._process_join_for_leafs(vm_host, vm_leaf, group_map, leaf_switch_update_count_map,
                                                 self.per_leaf_switch_update_count_map)
                    if add_leaf_to_pod:
                        self._process_join_for_pods(vm_leaf, vm_pod, group_map, pod_switch_update_count_map,
                                                    self.per_pod_switch_update_count_map)

                    if vm_type == 'S':
                        virtual_switch_update_count_map[-1] += 1
                        self.per_virtual_switch_update_count_map[vm_host] += 1
                    for vm in vms:
                        vm_host = vm_to_host_map[vm]

                        if vms_types[vm] == 'P' or vms_types[vm] == 'B':
                            virtual_switch_update_count_map[-1] += 1
                            self.per_virtual_switch_update_count_map[vm_host] += 1
            else:  # if event_type == 'L'
                vm = random.sample(vms, 1)[0]
                vm_host = vm_to_host_map[vm]
                vm_type = vms_types[vm]
                vms.remove(vm)
                del vms_types[vm]
                switch_group_size_map += [group_map['size']]
                group_map['size'] -= 1

                if vm_type == 'P':
                    virtual_switch_update_count_map[-1] += 1
                    self.per_virtual_switch_update_count_map[vm_host] += 1
                else:
                    vm_leaf = int(vm_host / self.num_hosts_per_leaf)
                    vm_pod = int(vm_leaf / self.num_leafs_per_pod)

                    self._process_leave_for_leafs(vm_host, vm_leaf, group_map, leaf_switch_update_count_map,
                                                  self.per_leaf_switch_update_count_map)
                    remove_leaf_from_pod = True if vm_leaf not in group_map['leafs_map'] else False
                    if remove_leaf_from_pod:
                        self._process_leave_for_pods(vm_leaf, vm_pod, group_map, pod_switch_update_count_map,
                                                     self.per_pod_switch_update_count_map)

                    if vm_type == 'S':
                        virtual_switch_update_count_map[-1] += 1
                        self.per_virtual_switch_update_count_map[vm_host] += 1
                    for vm in vms:
                        vm_host = vm_to_host_map[vm]

                        if vms_types[vm] == 'P' or vms_types[vm] == 'B':
                            virtual_switch_update_count_map[-1] += 1
                            self.per_virtual_switch_update_count_map[vm_host] += 1

    def process_with_failures(self, failed_node, vm_to_host_map, group_map):
        leafs_map = group_map['leafs_map']
        pods_map = group_map['pods_map']
        vms = group_map['vms']
        vms_types = group_map['vms_types']

        per_virtual_switch_update_count = self.with_failures_map['per_virtual_switch_update_count']

        if self.failed_node_type == 'spine':
            if len(leafs_map) <= 1:
                pass
            else:
                pubs = {'local': [], 'foreign': []}
                has_local_subs_per_leaf = [False] * self.num_leafs
                failed_pod = int(failed_node / self.num_spines_per_pod)

                for vm in vms:
                    vm_host = vm_to_host_map[vm]
                    vm_type = vms_types[vm]
                    vm_leaf = int(vm_host / self.num_hosts_per_leaf)
                    vm_pod = int(vm_leaf / self.num_leafs_per_pod)

                    if vm_type == 'P' or vm_type == 'B':
                        if vm_pod == failed_pod:
                            pubs['local'].append(vm)
                        else:
                            pubs['foreign'].append(vm)

                    if vm_type == 'S' or vm_type == 'B':
                        if vm_pod == failed_pod:
                            has_local_subs_per_leaf[vm_leaf] = True

                for vm in pubs['local']:
                    vm_host = vm_to_host_map[vm]
                    vm_leaf = int(vm_host / self.num_hosts_per_leaf)

                    if any([v for l, v in enumerate(has_local_subs_per_leaf) if l != vm_leaf]):
                        per_virtual_switch_update_count[vm_host] += 1

                has_local_subs = any(has_local_subs_per_leaf)

                if has_local_subs:
                    for vm in pubs['foreign']:
                        vm_host = vm_to_host_map[vm]
                        per_virtual_switch_update_count[vm_host] += 1

                if len(pubs['local']) != 0 or (has_local_subs and len(pubs['foreign']) != 0):
                    self.with_failures_map['group_count'] += 1
        elif self.failed_node_type == 'core':
            if len(pods_map) <= 1:
                pass
            else:
                pubs = []
                has_local_subs_per_pod = [False] * self.num_pods

                for vm in vms:
                    vm_host = vm_to_host_map[vm]
                    vm_type = vms_types[vm]
                    vm_leaf = int(vm_host / self.num_hosts_per_leaf)
                    vm_pod = int(vm_leaf / self.num_leafs_per_pod)

                    if vm_type == 'P' or vm_type == 'B':
                        pubs.append(vm)

                    if vm_type == 'S' or vm_type == 'B':
                        has_local_subs_per_pod[vm_pod] = True

                for vm in pubs:
                    vm_host = vm_to_host_map[vm]
                    vm_leaf = int(vm_host / self.num_hosts_per_leaf)
                    vm_pod = int(vm_leaf / self.num_leafs_per_pod)

                    if any([v for p, v in enumerate(has_local_subs_per_pod) if p != vm_pod]):
                        per_virtual_switch_update_count[vm_host] += 1

                if len(pubs) != 0:
                    self.with_failures_map['group_count'] += 1
