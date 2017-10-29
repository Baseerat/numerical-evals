import simulation.algorithms.naive as naive
import simulation.algorithms.exact_match as exact_match


def run(algorithm, data, max_bitmaps, max_leafs_per_bitmap, leafs_to_rules_count_map, max_rules_per_leaf, num_hosts_per_leaf):
    if algorithm == 'naive':
        naive.run(data, max_bitmaps, leafs_to_rules_count_map, max_rules_per_leaf, num_hosts_per_leaf)
    elif algorithm == 'exact_match':
        exact_match.run(data, max_bitmaps, max_leafs_per_bitmap, leafs_to_rules_count_map, max_rules_per_leaf, num_hosts_per_leaf)
    else:
        raise (Exception("invalid algorithm"))

