#!/usr/bin/env python2
############################################################
# Localisation test bench (boat dynamics simulation): 
#     to be used with test_bench_intervals_ros
############################################################     

import rospy

from roblib import *


from numpy import pi, array, asarray
from numpy.random import uniform

from std_msgs.msg import Float32, String
from geometry_msgs.msg import Vector3



##################################################################################################
################################  SIMULATION FUNCTIONS   #########################################

# Evolution equation
def evolX(X, u):
	"""Returns the derivative of X."""
	X, u = X.flatten(), u.flatten()
	x, y, theta, v = X[0], X[1], X[2], X[3]
	
	dX = array([[v*cos(theta)], [v*sin(theta)], [u[1]], [u[0]]])
	
	return dX


def getAzimuths(X, landmarks):
	"""Returns the bearing for the designated landmark."""
	x, y = X[0, 0], X[1, 0]
	azimuths = []
	for landmark in landmarks:
		xl, yl = landmark[0], landmark[1]        
		camera_measure = sawtooth(atan2(yl-y, xl-x) - X[2,0])
		compass_measure = X[2,0]
		azimuths.append(camera_measure+compass_measure)  #Interval(camera_measure+compass_measure-accuracy, camera_measure+compass_measure+accuracy))
	return azimuths


def inRange(X, landmarks, perceptionAngle, visionRange):
	"""Returns the list of the landmarks that the boat is really able to see."""
	spotted = []
	for m in landmarks:
		dist = norm(X[:2]-asarray(m).reshape((2,1)))
		bearing = sawtooth(atan2(m[1]-X[1,0], m[0]-X[0,0]) - X[2,0])
		if dist < visionRange and np.abs(bearing) < perceptionAngle:
			spotted.append(m)            
	return spotted




##################################################################################################
################################   Commands subscriber   #########################################
def sub_operator(data):
	global speed_command, rotation_command
	speed_command = data.y
	rotation_command = data.x






def run():
	global speed_command, rotation_command


##################################################################################################
################################       Setup        ##############################################


	# Estimated specification of sensors
	heading_accuracy = rospy.get_param('heading_accuracy', 5) *pi/180     # Compass + camera accuracy to compute the azimuth of a buoy
	range_of_vision = rospy.get_param('range_of_vision', 15)              # maximum distance for mark detection
	angle_of_perception = rospy.get_param('angle_of_perception', 50) *pi/180   # angle of perception of the camera
	speed_accuracy = rospy.get_param('speed_accuracy', 0.3)              # accuracy on speed measurement.

	# Integration step
	dt = rospy.get_param('integration_step', 0.2)            

	# Initial state of the boat
	Xinit = array([[30], [30], [pi/2], [0.1]])

	# Landmarks
	landmarks = [[35, 70], [75,95], [25,120]]


##################################################################################################
############################    ROS initialisation      ##########################################

	rospy.init_node("boat_simulation")

	rate = rospy.Rate(1/dt)

	pub_heading = rospy.Publisher("heading", Float32, queue_size = 2)
	pub_speed = rospy.Publisher("speed", Float32, queue_size = 2)
	pub_buoys = rospy.Publisher("buoys_directions", String, queue_size = 2)
	pub_boat = rospy.Publisher("state_truth", String, queue_size = 2)
	rospy.Subscriber("commands", Vector3, sub_operator)

	# Initialising variables
	X = Xinit
	speed_command = 0.
	rotation_command = 0.

	while not rospy.is_shutdown():

##################################################################################################
################################     Evolution      ##############################################

		# command
		u = array([[speed_command], [rotation_command]]) 

		# evolution
		dX = evolX(X, u)        
		X = X + dt*dX
		X[2] = sawtooth(X[2])

		rate.sleep()

##################################################################################################
################################   Measures simulation    ########################################

		boat_speed = X[3,0] + uniform(-speed_accuracy, speed_accuracy)
		boat_heading = X[2,0] + uniform(-heading_accuracy, heading_accuracy)

		pub_heading.publish(Float32(data=boat_heading))
		pub_speed.publish(Float32(data=boat_speed))

		spotted = inRange(X, landmarks, angle_of_perception, range_of_vision)
		marks_directions = getAzimuths(X, spotted) 

		pub_buoys.publish(String(data=str(marks_directions)))

		pub_boat.publish(String(data=str(X.tolist())))




if __name__ == "__main__":
	run()