import simulation.algorithms.single_match as single_match
import simulation.algorithms.exact_match as exact_match
import simulation.algorithms.greedy_match as greedy_match
import simulation.algorithms.fuzzy_match as fuzzy_match
import simulation.algorithms.random_fuzzy_match as random_fuzzy_match


def run(algorithm, data, max_bitmaps, max_leafs_per_bitmap, redundancy_per_bitmap, leafs_to_rules_count_map,
        max_rules_per_leaf):
    if algorithm == 'single_match':
        single_match.run(data, max_bitmaps, leafs_to_rules_count_map, max_rules_per_leaf)
    elif algorithm == 'exact_match':
        exact_match.run(data, max_bitmaps, max_leafs_per_bitmap, leafs_to_rules_count_map, max_rules_per_leaf)
    elif algorithm == 'greedy_match':
        greedy_match.run(data, max_bitmaps, max_leafs_per_bitmap, redundancy_per_bitmap, leafs_to_rules_count_map,
                         max_rules_per_leaf)
    elif algorithm == 'fuzzy_match':
        fuzzy_match.run(data, max_bitmaps, max_leafs_per_bitmap, redundancy_per_bitmap, leafs_to_rules_count_map,
                        max_rules_per_leaf)
    elif algorithm == 'random_fuzzy_match':
        random_fuzzy_match.run(data, max_bitmaps, max_leafs_per_bitmap, redundancy_per_bitmap,
                               leafs_to_rules_count_map, max_rules_per_leaf)
    else:
        raise (Exception("invalid algorithm"))

