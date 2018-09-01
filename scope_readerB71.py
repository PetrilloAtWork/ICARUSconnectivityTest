#written by Sergi Castells and some small additions by Brenda Gomez

import subprocess as sp
from struct import unpack
import sys, os
import time
import visa
import numpy as np
from DataLoader import DataLoader

delim = ',' #change default deliminator as needed
user = "castells"
location = "/icarus/app/users/castells/my_test_area/waveform_analysis"
folder_name = "temp_folder71"

def test_writeFile(filename):
	with open("%s.csv" % filename, "w") as file:
		for i in range(100):
			file.write("100%s29\n" % delim)


def readFile(filename):
	line_value = []
	with open(filename) as file:
		for line in file:
			line_value.append(line)
	
	return line_value


def parseFile(line):
	line_value = line.split(delim)
	line_value[len(line_value)-1] = line_value[len(line_value)-1].strip('\n')
	
	return line_value


def savePeaks(lines):
	h = []
	x = []
	y = []
	w = []
	n = []
	for i in range(len(lines)):
		line_value = parseFile(lines[i])
		h.append(float(line_value[4]))
		x.append(float(line_value[1]))
		y.append(float(line_value[2]))
		w.append(float(line_value[3]))
		n.append(float(line_value[0]))
	
	items = [h,x,y,w,n]
	return items


def saveAtts(lines):
	b = []
	s = []
	n = []
	for i in range(len(lines)):
		line_value = parseFile(lines[i])
		b.append(float(line_value[1]))
		s.append(float(line_value[2]))
		n.append(float(line_value[0]))
	
	items = [n,b,s]
	return items


def fileLength(filename):
	count = 0
	with open(filename) as file:
		for line in file:
			count += 1
	
	return count - 1


def getWaveform(channel):
	#tells scope channel, encoding, # of data points, # of points to keep
	rm = visa.ResourceManager()
	scopeID = 'TCPIP0::192.168.230.71::INSTR'
	data_points = "10000"
	scope = rm.open_resource(scopeID)
	scope.write('DATa:SOURce %s' % (channel))
	scope.write('DATa:ENCdg RPB')
	scope.write('DATa:WIDth 1')
	scope.write('DATa:STARt 1')
	scope.write('DATa:STOP %s' % (data_points))

	ymult = float(((scope.query('WFMPRE:YMULT?')).split(' '))[1])
	yzero = float(((scope.query('WFMPRE:YZERO?')).split(' '))[1])
	yoff = float(((scope.query('WFMPRE:YOFF?')).split(' '))[1])
	xincr = float(((scope.query('WFMPRE:XINCR?')).split(' '))[1])

	scope.write('CURVE?')
	data = scope.read_raw()

	#the value for 13 accounts for and removes :CURV #510000
	ADC_wave = data[13:-1]
        
        ADC_wave = np.array(unpack('%sB' % len(ADC_wave),ADC_wave))

	#this is units of volts and milliseconds
	Volts = (ADC_wave - yoff) * ymult  + yzero
	Time = np.arange(0, xincr * len(Volts), xincr)
        
	#creates and fills numpy array (2x10000)
	data = np.empty(shape=(2, int(data_points)))

	#fill data array with voltage and time values
	data_iterator = 0
	for i in np.nditer(Volts):
		data[0,data_iterator] = i
		data_iterator += 1
        
	data_iterator = 0
	for i in np.nditer(Time):
		data[1,data_iterator] = i
		data_iterator += 1
        
	#writes data array to file in csv format
	filename = "%s.csv" % (channel)
	with open(filename, 'w+') as file:
		for i in range(int(data_points)):
			line = str(data[1,i]) + "," + str(data[0,i])
			file.write(line + "\n")

	return channel


def uploadData(prefix):
	#	Order of entries for test information in test_stas.csv
	#	
	#	Operator				OP				string
	#	Waveform ID			WVID			int
	#	Test ID					TID				int
	#	Wire Number			WRN				int
	#	Wire Plane			WRP				int
	#	Chimney					CHM				string
	#	Input Chimney		I_CHM			string
	#	Input Cable			I_CBL			string
	#	Date						DT				string
	#	Comment					CM				string
	#
	
	test_stats = readFile("test_stats.csv")
	data = parseFile(test_stats[0])
	OP = data[0]
	WVID = int(data[1])
	TID = int(data[2])
	WRN = int(data[3])
	WRP = int(data[4])
	CHM = data[5]
	I_CHM = data[6]
	I_CBL = data[7]
	DT = data[8]
	
	print("\n" + "-" * 20)
	print("Operator: \t%s" % (OP))
	print("Waveform ID: \t%d" % (WVID))
	print("Test ID: \t%d" % (TID))
	print("Wire Number: \t%d%s" % (WRN," + next 3"))
	print("Wire Plane: \t%d" % (WRP))
	print("Chimney: \t%s" % (CHM))
	print("Input Chimney: \t%s" % (I_CHM))
	print("Input Cable: \t%s" % (I_CBL))
	print("Date: \t\t%s" % (DT))
	print("-" * 20 + "\n")
	
	check = True
	
	sp.check_output(['mv','./%s/waveforms.root' % folder_name,'./%s/test_%s_%s.root' % (folder_name,WRP,WRN)])
	
	password = os.environ.get("LOADER_PWD", "v9kecos3")
	url = "https://dbweb6.fnal.gov:8443/hdb/icarusdev/loader"
	group = "Continuity Tables" 
	table_pulse = "test_pulse_mappings"
	table_wave = "continuity_test_waveforms"
	table_peak = "continuity_peak_waveforms"
	
	while(check == True):
		verify = raw_input("Current test parameters set. Save test data to database? (Y/n): ")
                
		if(verify == "Y"):
			check = False
			wave_atts = saveAtts(readFile('./%s/waveform_attributes.csv' % folder_name))
			WV_BASELINE = wave_atts[1]
			WV_NOISE = wave_atts[2]
			WV_PEAKS = wave_atts[0]
			
			peak_data = savePeaks(readFile('./%s/signal_stats.csv' % folder_name))
			P_ID = peak_data[4]
			P_XVALUE = peak_data[1]
			P_HEIGHT = peak_data[2]
			P_WIDTH = peak_data[3]
                        
			with open("waveform_list.txt","r") as file:
					j = []
					for line in file:
							j.append(line.strip('\n'))
							j[-1] = j[-1][j[-1].find("_")+1:-4]
                        
			for i in range(len(WV_BASELINE)):
				baseline = float(WV_BASELINE[i])
				std_dev = float(WV_NOISE[i])
				peaks = int(WV_PEAKS[i])
				peak_total = -1
				
				if(peaks == 0):
					peak_total += 1
				else:
					peak_total += peaks
				
				row_pulse = {
					'wire_plane': WRP,
					'wire_number': WRN,
					'chimney': CHM,
					'input_chimney': I_CHM,
					'input_cable': I_CBL,
				}
				
				dataLoader_pulse = DataLoader(password, url, group, table_pulse)
				dataLoader_pulse.addRow(row_pulse)	
				(retVal1, code1, text1) = dataLoader_pulse.send()
				dataLoader_pulse.clearRows()
				
				if retVal1:
					#successfully uploaded data
					pass
				else:
					print "Failed!" 
					print code1
					print text1
					sys.exit(1)
				
				row_wave = {
					'waveform_id': WVID,
					'test_id': TID,
					'test_date': DT,
					'wire_plane': WRP,
					'wire_number': WRN,
					'baseline': baseline,
					'standard_deviation': std_dev,
					'histogram': open("./%s/%s%s.gif" % (folder_name,prefix,j[i]), "rb"),
					'fft': open("./%s/%s%sFFT.gif" % (folder_name,prefix,j[i]), "rb"),
					'operator': OP,
				}
                                
				dataLoader_wave = DataLoader(password, url, group, table_wave)
				dataLoader_wave.addRow(row_wave)
				(retVal2, code2, text2) = dataLoader_wave.send()
				dataLoader_wave.clearRows()
				
				if retVal2:
					#successfully uploaded data
					pass
				else:
					print "Failed!"
					print code2
					print text2
					sys.exit(1)
				
				for i in range(peaks):
					peak_id = int(P_ID[i+peak_total])
					height = float(P_HEIGHT[i+peak_total])
					width = float(P_WIDTH[i+peak_total])
					x_value = float(P_XVALUE[i+peak_total])
					
					row_peak = {
						'waveform_id': WVID,
						'test_id': TID,
						'peak_id': peak_id,
						'height': height,
						'width': width,
						'peak_time': x_value,
					}
					
					dataLoader_peak = DataLoader(password, url, group, table_peak)
					dataLoader_peak.addRow(row_peak)
					(retVal3, code3, text3) = dataLoader_peak.send()
					dataLoader_peak.clearRows()
					
					if retVal3:
						#successfully uploaded data
						pass
					else:
						print "Failed!"
						print code3
						print text3
						sys.exit(1)	
					
				WVID += 1
				WRN += 1
			
			with open("test_stats.csv", "w+") as file:
				file.write("%s,%s,%s,%s,%s,%s,%s,%s,%s" % (OP,WVID,TID,WRN,WRP,CHM,I_CHM,I_CBL,DT))
		
		elif(verify == "n"):
			check = False
			print("Test data not saved to database. Access test results in corresponding files or run test again.")
		
		else:
			print("Select a valid response... \n")


def fullAnalysis():
	#run py-VISA code here
	ch1_name = getWaveform("CH1")
	ch2_name = getWaveform("CH2")
	ch3_name = getWaveform("CH3")
	ch4_name = getWaveform("CH4")

	#run ROOT/C++ code here (via command line)
	sp.check_output(['scp','./CH1.csv','%s@icarusgpvm01.fnal.gov:%s/' % (user,location)])
	sp.check_output(['scp','./CH2.csv','%s@icarusgpvm01.fnal.gov:%s/' % (user,location)])
	sp.check_output(['scp','./CH3.csv','%s@icarusgpvm01.fnal.gov:%s/' % (user,location)])
	sp.check_output(['scp','./CH4.csv','%s@icarusgpvm01.fnal.gov:%s/' % (user,location)])
        
	sp.check_output(['cp','./CH1.csv','./%s' % folder_name])
	sp.check_output(['cp','./CH2.csv','./%s' % folder_name])
	sp.check_output(['cp','./CH3.csv','./%s' % folder_name])
	sp.check_output(['cp','./CH4.csv','./%s' % folder_name])

	sp.call(['ssh','-tt','%s@icarusgpvm01.fnal.gov' % user,'source mv2ic.sh waveform_analysis n; root -b -q -l run_slow.c'])
        
 	sp.check_output(['scp','%s@icarusgpvm01.fnal.gov:%s/signal_stats.csv' % (user,location),'./%s' % folder_name])
	sp.check_output(['scp','%s@icarusgpvm01.fnal.gov:%s/waveform_attributes.csv' % (user,location),'./%s' % folder_name])
	sp.check_output(['scp','%s@icarusgpvm01.fnal.gov:%s/waveforms.root' % (user,location),'./%s' % folder_name])

	sp.check_output(['scp','%s@icarusgpvm01.fnal.gov:%s/CH1.gif' % (user,location),'./%s' % folder_name])
	sp.check_output(['scp','%s@icarusgpvm01.fnal.gov:%s/CH1FFT.gif' % (user,location),'./%s' % folder_name])
	sp.check_output(['scp','%s@icarusgpvm01.fnal.gov:%s/CH2.gif' % (user,location),'./%s' % folder_name])
	sp.check_output(['scp','%s@icarusgpvm01.fnal.gov:%s/CH2FFT.gif' % (user,location),'./%s' % folder_name])
	sp.check_output(['scp','%s@icarusgpvm01.fnal.gov:%s/CH3.gif' % (user,location),'./%s' % folder_name])
	sp.check_output(['scp','%s@icarusgpvm01.fnal.gov:%s/CH3FFT.gif' % (user,location),'./%s' % folder_name])
	sp.check_output(['scp','%s@icarusgpvm01.fnal.gov:%s/CH4.gif' % (user,location),'./%s' % folder_name])
	sp.check_output(['scp','%s@icarusgpvm01.fnal.gov:%s/CH4FFT.gif' % (user,location),'./%s' % folder_name])

	sp.check_output(['reset'])
	sp.check_output(['clear'])
        
	uploadData('CH')

def quickAnalysis(NWF,CHIMNEY,INDUCTION_WIRE,POSITION):
	for i in range(NWF):


          with open('waveform_id_71.txt','r') as file:
            ID = file.readline().strip('\n')

        with open('waveform_list_71.txt','a') as file:
             ID = int(ID) - 1

             for i in range(NWF):
                 ID += 1
                 file.write('waveform_%s_%s_%s_%s_%s.csv\n' % ('CH1',CHIMNEY,INDUCTION_WIRE,POSITION,ID))
                 file.write('waveform_%s_%s_%s_%s_%s.csv\n' % ('CH2',CHIMNEY,INDUCTION_WIRE,POSITION,ID))
                 file.write('waveform_%s_%s_%s_%s_%s.csv\n' % ('CH3',CHIMNEY,INDUCTION_WIRE,POSITION,ID))
                 file.write('waveform_%s_%s_%s_%s_%s.csv\n' % ('CH4',CHIMNEY,INDUCTION_WIRE,POSITION,ID))

                 getWaveform('CH1')
                 getWaveform('CH2')
                 getWaveform('CH3')
                 getWaveform('CH4')

                 sp.call(['mv','CH1.csv','./%s/waveform_%s_%s_%s_%s_%s.csv' % (folder_name,'CH1',CHIMNEY,INDUCTION_WIRE,POSITION,ID)])
                 sp.call(['mv','CH2.csv','./%s/waveform_%s_%s_%s_%s_%s.csv' % (folder_name,'CH2',CHIMNEY,INDUCTION_WIRE,POSITION,ID)])
                 sp.call(['mv','CH3.csv','./%s/waveform_%s_%s_%s_%s_%s.csv' % (folder_name,'CH3',CHIMNEY,INDUCTION_WIRE,POSITION,ID)])
                 sp.call(['mv','CH4.csv','./%s/waveform_%s_%s_%s_%s_%s.csv' % (folder_name,'CH4',CHIMNEY,INDUCTION_WIRE,POSITION,ID)])


        with open('waveform_id_71.txt','w') as file:
            file.write(str(ID + 1))



def analyzeAll():
	run_list = []
	
	for filename in os.listdir("./%s/" % folder_name):
		if filename.endswith(".csv") and filename != "signal_stats.csv" and filename != "waveform_attributes.csv":
			run_list.append('''\treadData("%s");\n\tmakeHist("%s");\n''' % (filename, filename[:-4]))
                        sp.call(['scp','./%s/%s' % (folder_name,filename),'%s@icarusgpvm01.fnal.gov:%s/' % (user,location)])
                        time.sleep(0.5)
	
	run_all = '''{
        gROOT->ProcessLine(".L analyze.c");

	useWaveformFile("waveforms.root");
'''
	
	for i in run_list:
		run_all = run_all + i


	run_all = run_all + '''
        examineWaveform("waveforms.root");
	signalStats("signal_stats");
	waveformAttributes("waveform_attributes");
        noiseFFT("waveforms.root");
}'''
        
	with open("run_all.c","w+") as file:
		file.write(run_all)
	
	sp.call(['scp','run_all.c','%s@icarusgpvm01.fnal.gov:%s/' % (user,location)])
	process = sp.Popen(['ssh','-tt','%s@icarusgpvm01.fnal.gov' % user,'source mv2ic.sh waveform_analysis n; root -b -q -l run_all.c'])
	process.wait()
	
	for filename in os.listdir("./%s/" % folder_name):
		if filename.endswith(".csv") and filename != "signal_stats.csv" and filename != "waveform_attributes.csv":
			filename_fix1 = filename[:-4] + ".gif"
			filename_fix2 = filename[:-4] + "FFT.gif"
			sp.call(['scp','%s@icarusgpvm01.fnal.gov:%s/%s' % (user,location,filename_fix1),'./%s/' % folder_name])
			sp.call(['scp','%s@icarusgpvm01.fnal.gov:%s/%s' % (user,location,filename_fix2),'./%s/' % folder_name])
	
	sp.call(['scp','%s@icarusgpvm01.fnal.gov:%s/signal_stats.csv' % (user,location),'./%s' % folder_name])
	sp.call(['scp','%s@icarusgpvm01.fnal.gov:%s/waveform_attributes.csv' % (user,location),'./%s' % folder_name])
	sp.call(['scp','%s@icarusgpvm01.fnal.gov:%s/waveforms.root' % (user,location),'./%s' % folder_name])
	
	#sp.check_output(['reset'])
	#sp.check_output(['clear'])
	
	uploadData('waveform_')

def regenList():
	with open("waveform_list.txt","w") as file:
		pass
                
	for filename in os.listdir("./%s/" % folder_name):
		if filename.endswith(".csv") and filename != "signal_stats.csv" and filename != "waveform_attributes.csv":
			with open("waveform_list.txt","a") as file:
				file.write(filename + "\n")

def resetStats():
	with open("test_stats.csv","w") as file:
		file.write("%s,1,1,1,1,chimney,input_chimney,input_cable,date" % user)
