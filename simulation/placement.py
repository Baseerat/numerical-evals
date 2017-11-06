import random
import multiprocessing
from joblib import Parallel, delayed
from simulation.utils import bar_range


def unwrap_tenant_groups_to_leafs_and_count_map(args, **kwargs):
    return Placement._get_tenant_groups_to_leafs_and_count_map_mproc(*args, **kwargs)


def unwrap_tenant_groups_leafs_to_hosts_and_bitmap_map(args, **kwargs):
    return Placement._get_tenant_groups_leafs_to_hosts_and_bitmap_map_mproc(*args, **kwargs)


class Placement:
    def __init__(self, data, dist='uniform',  # options: uniform, colocate-random-linear, colocate-random-random
                 num_bitmaps=32, num_hosts_per_leaf=48, multi_threaded=False, num_jobs=4):
        self.data = data
        self.dist = dist
        self.num_bitmaps = num_bitmaps
        self.placement_num_hosts_per_leaf = num_hosts_per_leaf
        self.multi_threaded = multi_threaded
        self.num_jobs = num_jobs

        self.network = self.data['network']
        self.network_maps = self.network['maps']

        self.num_leafs = self.network['num_leafs']
        self.num_hosts_per_leaf = self.network['num_hosts_per_leaf']

        self.tenants = self.data['tenants']
        self.tenants_maps = self.tenants['maps']

        self.num_hosts = self.tenants['num_hosts']
        self.num_tenants = self.tenants['num_tenants']
        self.max_vms_per_host = self.tenants['max_vms_per_host']

        self.data['placement'] = {'dist': dist,
                                  'num_bitmaps': num_bitmaps,
                                  'num_hosts_per_leaf': num_hosts_per_leaf}
        self.placement = self.data['placement']

        for t in range(self.tenants['num_tenants']):
            self.tenants_maps[t]['vms_map'] = \
                [{'host': None, 'leaf': None} for _ in range(self.tenants_maps[t]['vm_count'])]

            group_count = self.tenants_maps[t]['group_count']
            groups_map = self.tenants_maps[t]['groups_map']
            for g in range(group_count):
                group_map = groups_map[g]
                group_map['leaf_count'] = None
                group_map['leafs'] = None
                group_map['leafs_map'] = dict()

        self._get_tenant_vms_to_host_map()
        self._get_tenant_vms_to_leaf_map()
        if not self.multi_threaded:
            self._get_tenant_groups_to_leafs_and_count_map()
            self._get_tenant_groups_leafs_to_hosts_and_bitmap_map()
        else:
            self._run_tenant_groups_to_leafs_and_count_map()
            self._run_tenant_groups_leafs_to_hosts_and_bitmap_map()

    def _uniform(self):
        available_hosts = [h for h in range(self.tenants['num_hosts'])]
        available_hosts_count = [0] * self.num_hosts

        for t in bar_range(self.num_tenants, desc='placement:vms->host'):
            hosts = random.sample(available_hosts, self.tenants_maps[t]['vm_count'])

            vms_map = self.tenants_maps[t]['vms_map']
            for v, host in enumerate(hosts):
                vms_map[v]['host'] = host
                available_hosts_count[host] += 1

            max_host_count = max(available_hosts_count)
            if max_host_count == self.max_vms_per_host:
                removed_hosts = [h for h, host_count in enumerate(available_hosts_count)
                                 if host_count == max_host_count]
                available_hosts = list(set(available_hosts) - set(removed_hosts))
                for removed_host in sorted(removed_hosts, reverse=True):
                    available_hosts_count[removed_host] = -1

    def _colocate_random_linear(self, is_sorted=False, is_reverse=False):
        available_leafs = [l for l in range(self.num_leafs)]
        available_hosts_per_leaf = [None] * self.num_leafs
        available_hosts_count_per_leaf = [None] * self.num_leafs

        for l in range(self.num_leafs):
            available_hosts_per_leaf[l] = [(l * self.num_hosts_per_leaf) + h
                                           for h in range(self.num_hosts_per_leaf)]
            available_hosts_count_per_leaf[l] = [0] * self.num_hosts_per_leaf

        if is_sorted:
            tenants_maps = sorted(self.tenants_maps, key=lambda item: item['vm_count'], reverse=is_reverse)
        else:
            tenants_maps = self.tenants_maps
        for t in bar_range(self.num_tenants, desc='placement:vms->host'):
            vms_map = tenants_maps[t]['vms_map']
            running_index = 0
            running_count = tenants_maps[t]['vm_count']
            while running_count > 0:
                selected_leaf = random.sample(available_leafs, 1)[0]
                selected_hosts_per_leaf = available_hosts_per_leaf[selected_leaf]
                selected_leaf_hosts_count = len(selected_hosts_per_leaf)
                selected_hosts_count_per_leaf = available_hosts_count_per_leaf[selected_leaf]

                # to ensure that we always pick hosts <= self.placement['num_hosts_per_leaf'] at each leaf
                if selected_leaf_hosts_count > self.placement_num_hosts_per_leaf:
                    selected_leaf_hosts_count = self.placement_num_hosts_per_leaf

                if int(running_count / selected_leaf_hosts_count) > 0:
                    for h in range(selected_leaf_hosts_count):
                        vms_map[running_index]['host'] = selected_hosts_per_leaf[h]
                        selected_hosts_count_per_leaf[h] += 1
                        running_index += 1
                    running_count -= selected_leaf_hosts_count
                else:
                    for h in range(running_count):
                        vms_map[running_index]['host'] = selected_hosts_per_leaf[h]
                        selected_hosts_count_per_leaf[h] += 1
                        running_index += 1
                    running_count = 0

                max_host_count = max(selected_hosts_count_per_leaf)
                if max_host_count == self.max_vms_per_host:
                    removed_hosts = [h for h, host_count in enumerate(selected_hosts_count_per_leaf)
                                     if host_count == max_host_count]
                    for removed_host in sorted(removed_hosts, reverse=True):
                        del selected_hosts_per_leaf[removed_host]
                        del selected_hosts_count_per_leaf[removed_host]

                    if len(selected_hosts_per_leaf) == 0:
                        available_leafs.remove(selected_leaf)

    def _colocate_random_random(self, is_sorted=False, is_reverse=False):
        available_leafs = [l for l in range(self.num_leafs)]
        available_hosts_per_leaf = [None] * self.num_leafs
        available_hosts_count_per_leaf = [None] * self.num_leafs

        for l in range(self.num_leafs):
            available_hosts_per_leaf[l] = [(l * self.num_hosts_per_leaf) + h
                                           for h in range(self.num_hosts_per_leaf)]
            available_hosts_count_per_leaf[l] = [0] * self.num_hosts_per_leaf

        if is_sorted:
            tenants_maps = sorted(self.tenants_maps, key=lambda item: item['vm_count'], reverse=is_reverse)
        else:
            tenants_maps = self.tenants_maps
        for t in bar_range(self.num_tenants, desc='placement:vms->host'):
            vms_map = tenants_maps[t]['vms_map']
            running_index = 0
            running_count = tenants_maps[t]['vm_count']
            while running_count > 0:
                selected_leaf = random.sample(available_leafs, 1)[0]
                selected_leaf_hosts = available_hosts_per_leaf[selected_leaf]
                selected_leaf_hosts_count = len(selected_leaf_hosts)
                selected_hosts_count_per_leaf = available_hosts_count_per_leaf[selected_leaf]

                # to ensure that we always pick hosts <= self.placement['num_hosts_per_leaf'] at each leaf
                if selected_leaf_hosts_count > self.placement_num_hosts_per_leaf:
                    selected_leaf_hosts = random.sample(selected_leaf_hosts, self.placement_num_hosts_per_leaf)
                    selected_leaf_hosts_count = self.placement_num_hosts_per_leaf

                if int(running_count / selected_leaf_hosts_count) > 0:
                    for h in range(selected_leaf_hosts_count):
                        vms_map[running_index]['host'] = selected_leaf_hosts[h]
                        selected_hosts_count_per_leaf[
                            available_hosts_per_leaf[selected_leaf].index(selected_leaf_hosts[h])] += 1
                        running_index += 1
                    running_count -= selected_leaf_hosts_count
                else:
                    for h in range(running_count):
                        vms_map[running_index]['host'] = selected_leaf_hosts[h]
                        selected_hosts_count_per_leaf[
                            available_hosts_per_leaf[selected_leaf].index(selected_leaf_hosts[h])] += 1
                        running_index += 1
                    running_count = 0

                max_host_count = max(selected_hosts_count_per_leaf)
                if max_host_count == self.max_vms_per_host:
                    removed_hosts = [h for h, host_count in enumerate(selected_hosts_count_per_leaf)
                                     if host_count == max_host_count]
                    for removed_host in sorted(removed_hosts, reverse=True):
                        del available_hosts_per_leaf[selected_leaf][removed_host]
                        del selected_hosts_count_per_leaf[removed_host]

                    if len(available_hosts_per_leaf[selected_leaf]) == 0:
                        available_leafs.remove(selected_leaf)

    def _get_tenant_vms_to_host_map(self):
        if self.dist == 'uniform':
            self._uniform()
        elif self.dist == 'colocate-random-linear':
            self._colocate_random_linear()
        elif self.dist == 'colocate-random-random':
            self._colocate_random_random()
        elif self.dist == 'sorted-colocate-random-linear':
            self._colocate_random_linear(is_sorted=True)
        elif self.dist == 'sorted-colocate-random-random':
            self._colocate_random_random(is_sorted=True)
        elif self.dist == 'reverse-sorted-colocate-random-linear':
            self._colocate_random_linear(is_sorted=True, is_reverse=True)
        elif self.dist == 'reverse-sorted-colocate-random-random':
            self._colocate_random_random(is_sorted=True, is_reverse=True)
        else:
            raise (Exception("invalid dist parameter for vm to host allocation"))

    def _get_tenant_vms_to_leaf_map(self):
        host_to_leaf_map = self.network_maps['host_to_leaf']
        for t in bar_range(self.num_tenants, desc='placement:vms->leaf'):
            vm_count = self.tenants_maps[t]['vm_count']
            vms_map = self.tenants_maps[t]['vms_map']
            for vm in range(vm_count):
                vms_map[vm]['leaf'] = host_to_leaf_map[vms_map[vm]['host']]

    def _get_tenant_groups_to_leafs_and_count_map(self):
        for t in bar_range(self.num_tenants, desc='placement:groups->leafs'):
            group_count = self.tenants_maps[t]['group_count']
            groups_map = self.tenants_maps[t]['groups_map']
            vms_map = self.tenants_maps[t]['vms_map']
            for g in range(group_count):
                group_map = groups_map[g]
                group_map['leafs'] = list({vms_map[vm]['leaf'] for vm in group_map['vms']})
                group_map['leaf_count'] = len(group_map['leafs'])

    @staticmethod
    def _get_tenant_groups_to_leafs_and_count_map_mproc(tenants_maps, num_tenants):
        for t in bar_range(num_tenants, desc='placement:groups->leafs'):
            group_count = tenants_maps[t]['group_count']
            groups_map = tenants_maps[t]['groups_map']
            vms_map = tenants_maps[t]['vms_map']
            for g in range(group_count):
                group_map = groups_map[g]
                group_map['leafs'] = list({vms_map[vm]['leaf'] for vm in group_map['vms']})
                group_map['leaf_count'] = len(group_map['leafs'])
        return tenants_maps

    def _run_tenant_groups_to_leafs_and_count_map(self):
        if (self.num_tenants % self.num_jobs) != 0:
            raise (Exception('input not divisible by num_jobs'))

        input_size = int(self.num_tenants / self.num_jobs)
        input_groups = [(i, i + input_size) for i in range(0, self.num_tenants, input_size)]
        inputs = [(self.tenants_maps[i:j],
                   input_size) for i, j in input_groups]

        # pool = multiprocessing.Pool()
        # results = pool.map(unwrap_tenant_groups_to_leafs_and_count_map, [i for i in inputs])

        num_cpus = multiprocessing.cpu_count()
        Parallel(n_jobs=num_cpus, backend="threading")(
            delayed(unwrap_tenant_groups_to_leafs_and_count_map)(i) for i in inputs)

    def _get_tenant_groups_leafs_to_hosts_and_bitmap_map(self):
        for t in bar_range(self.num_tenants, desc='placement:leafs->bitmap'):
            group_count = self.tenants_maps[t]['group_count']
            groups_map = self.tenants_maps[t]['groups_map']
            vms_map = self.tenants_maps[t]['vms_map']

            for g in range(group_count):
                group_map = groups_map[g]
                for vm in group_map['vms']:
                    vm_map = vms_map[vm]
                    if vm_map['leaf'] in group_map['leafs_map']:
                        group_map['leafs_map'][vm_map['leaf']]['hosts'] |= {vm_map['host']}
                    else:
                        group_map['leafs_map'][vm_map['leaf']] = dict()
                        group_map['leafs_map'][vm_map['leaf']]['hosts'] = {vm_map['host']}

                leafs_map = group_map['leafs_map']
                for l in group_map['leafs_map']:
                    leaf_map = leafs_map[l]
                    leaf_map['bitmap'] = 0

                    for h in leaf_map['hosts']:
                        leaf_map['bitmap'] |= 1 << (h % self.num_hosts_per_leaf)

    @staticmethod
    def _get_tenant_groups_leafs_to_hosts_and_bitmap_map_mproc(tenants_maps, num_tenants, num_hosts_per_leaf):
        for t in bar_range(num_tenants, desc='placement:leafs->bitmap'):
            group_count = tenants_maps[t]['group_count']
            groups_map = tenants_maps[t]['groups_map']
            vms_map = tenants_maps[t]['vms_map']

            for g in range(group_count):
                group_map = groups_map[g]
                for vm in group_map['vms']:
                    vm_map = vms_map[vm]
                    if vm_map['leaf'] in group_map['leafs_map']:
                        group_map['leafs_map'][vm_map['leaf']]['hosts'] |= {vm_map['host']}
                    else:
                        group_map['leafs_map'][vm_map['leaf']] = dict()
                        group_map['leafs_map'][vm_map['leaf']]['hosts'] = {vm_map['host']}

                leafs_map = group_map['leafs_map']
                for l in group_map['leafs_map']:
                    leaf_map = leafs_map[l]
                    leaf_map['bitmap'] = 0

                    for h in leaf_map['hosts']:
                        leaf_map['bitmap'] |= 1 << (h % num_hosts_per_leaf)
        return tenants_maps

    def _run_tenant_groups_leafs_to_hosts_and_bitmap_map(self):
        if (self.num_tenants % self.num_jobs) != 0:
            raise (Exception('input not divisible by num_jobs'))

        input_size = int(self.num_tenants / self.num_jobs)
        input_groups = [(i, i + input_size) for i in range(0, self.num_tenants, input_size)]
        inputs = [(self.tenants_maps[i:j],
                   input_size,
                   self.num_hosts_per_leaf) for i, j in input_groups]

        # pool = multiprocessing.Pool()
        # results = pool.map(unwrap_tenant_groups_leafs_to_hosts_and_bitmap_map, [i for i in inputs])

        num_cpus = multiprocessing.cpu_count()
        Parallel(n_jobs=num_cpus, backend="threading")(
            delayed(unwrap_tenant_groups_leafs_to_hosts_and_bitmap_map)(i) for i in inputs)
