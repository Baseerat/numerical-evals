import os
import sys
import random
from simulation.data import Data
from simulation.utils import marshal_load_obj

if len(sys.argv) > 1:
    LOG_CLOUD_STATS = True if sys.argv[1] == 'True' else False
    NUM_CORES = int(sys.argv[2])
    NUM_SPINES_PER_POD = int(sys.argv[3])
    DATA_FILE = sys.argv[4]
    LOG_DIR = sys.argv[5]

    _TEMP = DATA_FILE.split('.')
    CLOUD_PARAMS = _TEMP[1].split('_')
    NUM_PODS = int(CLOUD_PARAMS[0])
    NUM_LEAFS_PER_POD = int(CLOUD_PARAMS[1])
    NUM_HOSTS_PER_LEAF = int(CLOUD_PARAMS[2])
    NUM_TENANTS = int(CLOUD_PARAMS[4])
    SEED = int(CLOUD_PARAMS[15])

    OPTIMIZER_PARAMS_0 = _TEMP[2].split('_')
    NODE_TYPE_0 = OPTIMIZER_PARAMS_0[7]

    if len(_TEMP) > 3:
        OPTIMIZER_PARAMS_1 = _TEMP[3].split('_')
        NODE_TYPE_1 = OPTIMIZER_PARAMS_1[7]
    else:
        OPTIMIZER_PARAMS_1 = []
        NODE_TYPE_1 = None

elif False:
    LOG_CLOUD_STATS = True
    NUM_CORES = 4
    NUM_SPINES_PER_POD = 4
    DATA_FILE = 'output/optimizer..'
    LOG_DIR = 'output/logs'

    CLOUD_PARAMS = []
    NUM_PODS = 12
    NUM_LEAFS_PER_POD = 48
    NUM_HOSTS_PER_LEAF = 48
    NUM_TENANTS = 3000
    SEED = 0

    OPTIMIZER_PARAMS_0 = []
    NUM_BITMAPS = 2
    NODE_TYPE_0 = 'pods'

    OPTIMIZER_PARAMS_1 = []
    NODE_TYPE_1 = None
elif False:
    LOG_CLOUD_STATS = False
    NUM_CORES = 4
    NUM_SPINES_PER_POD = 4
    DATA_FILE = 'output/optimizer...'
    LOG_DIR = 'output/logs'

    CLOUD_PARAMS = []
    NUM_PODS = 12
    NUM_LEAFS_PER_POD = 48
    NUM_HOSTS_PER_LEAF = 48
    NUM_TENANTS = 3000
    SEED = 0

    OPTIMIZER_PARAMS_0 = []
    NODE_TYPE_0 = 'leafs'

    OPTIMIZER_PARAMS_1 = []
    NODE_TYPE_1 = None
elif False:
    LOG_CLOUD_STATS = True
    NUM_CORES = 4
    NUM_SPINES_PER_POD = 4
    DATA_FILE = 'output/optimizer..'
    LOG_DIR = 'output/logs'

    CLOUD_PARAMS = []
    NUM_PODS = 12
    NUM_LEAFS_PER_POD = 48
    NUM_HOSTS_PER_LEAF = 48
    NUM_TENANTS = 30
    SEED = 0

    OPTIMIZER_PARAMS_0 = []
    NODE_TYPE_0 = 'leafs'

    OPTIMIZER_PARAMS_1 = []
    NODE_TYPE_1 = None
else:
    raise (Exception('invalid parameters'))

random.seed(SEED)

if OPTIMIZER_PARAMS_1:
    log_dir = LOG_DIR + "." + "_".join(CLOUD_PARAMS) + "." + "_".join(OPTIMIZER_PARAMS_0) + \
              "." + "_".join(OPTIMIZER_PARAMS_1)
else:
    log_dir = LOG_DIR + "." + "_".join(CLOUD_PARAMS) + "." + "_".join(OPTIMIZER_PARAMS_0)

if os.path.isdir(log_dir):
    print('%s, already exists.' % log_dir)
    exit(0)

os.system('mkdir -p %s' % log_dir)

data = marshal_load_obj(DATA_FILE)

data = Data(data, num_tenants=NUM_TENANTS, num_cores=NUM_CORES, num_pods=NUM_PODS,
            num_spines_per_pod=NUM_SPINES_PER_POD, num_leafs_per_pod=NUM_LEAFS_PER_POD,
            num_hosts_per_leaf=NUM_HOSTS_PER_LEAF, log_dir=log_dir, node_type_0=NODE_TYPE_0, node_type_1=NODE_TYPE_1)

data.log_stats(log_cloud_stats=LOG_CLOUD_STATS)
