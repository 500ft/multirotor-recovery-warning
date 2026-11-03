Raw flight data of the propeller damage experiments conducted to detect loss of stability with increasing blade damage severity. 

Two data subsets are available: 
1. Autonomous flight experiments are conducted with a quadrotor called "DragonFly". These include trajectory (circles and positional set points) and hover tracking tasks in both windless and windy conditions. Autonomous flight is facilitated by the Indiflight control software (available here: https://github.com/tudelft/INDIFlight).
2. Manual (i.e. human piloted) flight experiments conducted with a quadrotor called "HoverFly". These include only hovering tasks for pilot behavior consistency. The flight controller used is BetaFlight (available here: https://www.betaflight.com/download)
Both quadrotor are constructed from off the shelf components and use the MATEKSYS H743-SLIM V3 flight controller on an Ethix CineRat frame. 

The folder structure is as follows:
- flight_dragonfly_exp 
	- Onboard
		- (... subfolders with raw data .csv files)
	- DragonFly_file_log.csv
	- DragonFlyConfig_CGI.json
	- FIDINFO.json
- flight_hoverfly_exp
	- Onboard
		- (... subfolders with raw data .csv files)
	- HoverFly_file_log.csv
	- HoverFlyConfig_CGI.json
	- FIDINFO.json


The respective config.json files describe useful properties of the quadrotor, such as the rotor location mapping, mass, propeller radii, and moment arm lengths. Note, however, that the moment of inertia is not accurate. 

The respective FIDINFO.json files outline the damage severity (as a %) and damage location of each flight identifier. 

The raw flight data is available as .csv files within the "Onboard" subfolder, where each file denotes an entire flight. Moreover, for both the DragonFly and HoverFly quadrotor, a corresponding file_log.csv is provided which describes details of each flight (e.g. flight identifier, (relative) location of data files, and comments/observations on the flight plan).


Due to the difference in flight controller logging, the raw data .csv files have slightly different fields. 
For the DragonFly: (Please widen window in notepad to see structure)
DESCRIPTION						- UNITS	- COLUMN NAME
Current loop integer 					-	- loopIteration
Time in microseconds 					- us	- timeUs
Remote controller commands (thrust, yaw, roll, pitch)	- 	- rcCommand[0],rcCommand[1],rcCommand[2],rcCommand[3]
Battery voltage (V)					- V	- vbatLatest
Current estimate (A)					- A	- amperageLatest
Receiver signal quality 				-	- rssi
Filtered gyroscope data (0:roll, 1:pitch, 2:yaw)	- deg/s	- gyroADC[0],gyroADC[1],gyroADC[2]
Raw filtered gyroscope data (0:roll, 1:pitch, 2:yaw)	- deg/s	- gyroADCafterRpm[0],gyroADCafterRpm[1],gyroADCafterRpm[2]
Filtered accelerometer data (0:x, 1:y, 2:z)		- m/s/s	- accSmooth[0],accSmooth[1],accSmooth[2]
Raw accelerometer data (0:x, 1:y, 2:z)			- m/s/s	- accADCafterRpm[0],accADCafterRpm[1],accADCafterRpm[2]
Commanded rotor speeds [min:0, max:2000, no units]	-	- motor[0],motor[1],motor[2],motor[3]
Quaternion attitude (qw, qx, qy, qz)			-	- quat[0],quat[1],quat[2],quat[3]
Estimated rotational acceleration (0:x, 1:y, 2:z)	-	- alpha[0],alpha[1],alpha[2]
Quaternion attitude setpoints (qw, qx, qy, qz)		-	- quatSp[0],quatSp[1],quatSp[2],quatSp[3]
Rotational rate setpoints (0:x, 1:y, 2:z)		- rad/s	- gyroSp[0],gyroSp[1],gyroSp[2]
Rotational acceleration setpoints (0:x, 1:y, 2:z)	- 	- alphaSp[0],alphaSp[1],alphaSp[2]
ESC Rotor speed measurements (0:w1, 1:w2, 2:w3, 3:w4)	- rad/s	- omega[0],omega[1],omega[2],omega[3]
Raw ESC Rotor speed measurements (0:w1, 1:w2, 2:w3, 3:w4) - rad/s - omegaUnfiltered[0],omegaUnfiltered[1],omegaUnfiltered[2],omegaUnfiltered[3]
Rotor speed acceleration (0:w1, 1:w2, 2:w3, 3:w4)	- 	- omega_dot[0],omega_dot[1],omega_dot[2],omega_dot[3]
Position (obtained via external Mocap) (0:x, 1:y, 2:z)	- m	- pos[0],pos[1],pos[2]
Motion capture (Mocap) time 				- s	- extTime
Position (obtained via external Mocap) (0:x, 1:y, 2:z)	- m	- extPos[0],extPos[1],extPos[2]
Position setpoint (0:x, 1:y, 2:z)			- m	- posSp[0],posSp[1],posSp[2]
Velocity (obtained via external Mocap) (0:x, 1:y, 2:z)	- m/s	- vel[0],vel[1],vel[2]
Velocity (obtained via external Mocap) (0:x, 1:y, 2:z)	- m/s	- extVel[0],extVel[1],extVel[2]
Velocity setpoint (0:x, 1:y, 2:z)			- m/s	- velSp[0],velSp[1],velSp[2]
Acceleration setpoint (0:x, 1:y, 2:z) 			- m/s/s - accSp[0],accSp[1],accSp[2]
Attitude (obtained via external Mocap) 			- deg	- extAtt[0],extAtt[1],extAtt[2]
Current flight mode					-	- flightModeFlags
Time milliseconds 					- ms	- timeMs
Time seconds						- s	- timeS


For the HoverFly: 
DESCRIPTION						- UNITS	- COLUMN NAME
Current loop integer 					-	- loopIteration
Time 							- s 	- time (s)
P-gain 							-	- axisP[0], axisP[1], axisP[2]
I-gain							-	- axisI[0], axisI[1], axisI[2]
D-gain							-	- axisD[0], axisD[1] 
Remote controller commands (thrust, yaw, roll, pitch)	- 	- rcCommand[0],rcCommand[1],rcCommand[2],rcCommand[3]
Voltage							- V	- vbatLatest (V)
Current 						- A	- amperageLatest (A)
Reciever signal strength 				-	- rssi
Filtered gyroscope data (0:roll, 1:pitch, 2:yaw)	- rad/s	- gyroADC[0] (rad/s), gyroADC[1] (rad/s), gyroADC[2] (rad/s)
Filtered acceleromter data (0:x, 1:y, 2:z)		- m/s/s	- accSmooth[0] (m/s/s), accSmooth[1] (m/s/s), accSmooth[2] (m/s/s)
ESC rotor speed measurements				- eRPM	- debug[0], debug[1], debug[2], debug[3]
Commanded rotor speeds					-	- motor[0], motor[1], motor[2], motor[3]
Attitude (note: heading = -yaw) 			- deg	- roll, pitch, heading
