#!/usr/bin/env python
import roslib; roslib.load_manifest('rosmln')

from rosmln.srv import *
from rosmln.msg import *
import rospy

from mlnQueryTool import MLNInfer

class Storage:
	inf = None
	config = None

	def __init__(self, config=None):
		if (self.__class__.inf is None):
			self.__class__.inf = MLNInfer()

		if (config is not None):
			if (config.mlnFiles != '' and config.db != '' and config.db != ''):
				self.__class__.config = config
	
	@staticmethod
	def getInstance(config=None):
		s = Storage(config)
		return (Storage.inf, Storage.config)
	


def handle_mln_query(req):
	inf, conf = Storage.getInstance(req.config)
	print conf.mlnFiles
	results = Storage.inf.run(conf.mlnFiles, conf.db, conf.method, req.query.queries, conf.engine, conf.output_filename,
				              saveResults=conf.saveResults, maxSteps=5000, logic=conf.logic, grammar=conf.grammar)
			
	tuple_list = []
	for atom, p in results.iteritems():
		tuple_list.append(AtomProbPair(atom, p))

	return MLNInterfaceResponse(MLNDatabase(tuple_list))

def mln_interface_server():
    rospy.init_node('rosmln')
    s = rospy.Service('mln_interface', MLNInterface, handle_mln_query)
    print "MLN is ready to be queried."
    rospy.spin()

if __name__ == "__main__":
    mln_interface_server()


