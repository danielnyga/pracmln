#!/usr/bin/env python
import sys

import rospy
from pracmln.utils import locs
from rosmln.srv import *
from rosmln.msg import *


def mln_interface_client(query, config=None):
    rospy.wait_for_service('mln_interface')
    try:
        mln_interface = rospy.ServiceProxy('mln_interface', MLNInterface)
        resp1 = mln_interface(query, config)
        return resp1.response
    except rospy.ServiceException, e:
        print('Service call failed: %s'%e)


def print_results(results):
    if not results.evidence:
        print('ERROR: Something went wrong...')
    else:
        print results


if __name__ == '__main__':
    mlnFiles = '{}/test/models/smokers/wts.pybpll.smoking-train-smoking.mln'.format(locs.user_data)
    db = '{}/test/models/smokers/smoking-test-smaller.db'.format(locs.user_data)
    queries = 'Smokes'
    output_filename = 'results.txt'
    query = MLNQuery(queries, None)
    config = MLNConfig(mlnFiles, db, 'GibbsSampler', output_filename, True,  'FirstOrderLogic', 'PRACGrammar')
    print_results(mln_interface_client(query, config))

    print('Without config parameters')
    print_results(mln_interface_client(query))

    print('Without evidence')
    config.db=''
    query = MLNQuery(queries, ['Cancer(Ann)', '!Cancer(Bob)', '!Friends(Ann,Bob)'])
    print_results(mln_interface_client(query, config))


