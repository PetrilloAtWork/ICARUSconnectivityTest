#include <iostream>
#include <vector>
#include "TH1F.h"
#include "TFile.h"
#include "TCanvas.h"
#include "TNtuple.h"
#include "TMath.h"
#include <string>
#include "TKey.h"
#include "TCollection.h"
#include "TVirtualFFT.h"
#include "TLatex.h"

//for the sake of not doing TMath::someFunction() all the time in various places
using namespace TMath;

//saves a test-stand histogram as .gif file
void saveHist(string name, string path)
{
	//load in from .root file and get some histogram
	TFile f_hist(path.c_str());
	TH1F* hist = (TH1F*)f_hist.Get(name.c_str());

	//prepare canvas for drawing and saving
	string name2 = name + ".gif";
	TCanvas* hist_canvas = new TCanvas("hist_canvas", "canvas");
	hist->Draw();
	hist_canvas->SaveAs(name2.c_str());

	//delete pointers
	delete hist;
	delete hist_canvas;
}


//overloaded saveHist function with x-axis and y-axis title options
void saveHist(string name, string path, string xaxis, string yaxis)
{
	//load in from .root file and get some histogram
	TFile f_hist(path.c_str());
	TH1F* hist = (TH1F*)f_hist.Get(name.c_str());

	//prepare canvas for drawing and saving
	string name2 = name + ".gif";
	TCanvas* hist_canvas = new TCanvas("hist_canvas", "canvas");
	hist->GetXaxis()->SetTitle(xaxis.c_str());
	hist->GetYaxis()->SetTitle(yaxis.c_str());
	hist->Draw();
	hist_canvas->SaveAs(name2.c_str());

	//delete pointers
	delete hist;
	delete hist_canvas;
}


//overloaded saveHist function with x- and y-axis title, opacity, and canvas color options
void saveHist(string name, string path, string xaxis, string yaxis, float opac, int color)
{
	//load in from .root file and get some histogram
	TFile f_hist(path.c_str());
	TH1F* hist = (TH1F*)f_hist.Get(name.c_str());

	//prepare canvas for drawing and saving
	string name2 = name + ".gif";
	TCanvas* hist_canvas = new TCanvas("hist_canvas", "canvas");
	hist->GetXaxis()->SetTitle(xaxis.c_str());
	hist->GetYaxis()->SetTitle(yaxis.c_str());
	hist_canvas->SetFillColorAlpha(color, opac);
	hist->Draw();
	hist_canvas->SaveAs(name2.c_str());

	//delete pointers
	delete hist;
	delete hist_canvas;
}


//creates file to save multiple waveform histograms at once
void useWaveformFile(string name)
{
	TFile* newFile = new TFile(name.c_str(), "RECREATE");
	delete newFile;
}


//overloaded useWaveformFile function updates file to save multiple waveform histograms at once
void useWaveformFile(string name, string path)
{
	TFile f_hist(path.c_str());
	TH1F* hist = (TH1F*)f_hist.Get(name.c_str());
	TFile* newFile = new TFile("waveforms.root", "UPDATE");

	hist->SetDirectory(0);
	hist->Write();
	newFile->Close();

	delete hist;
	delete newFile;
}


//convert .txt (.CSV) file to something readable by ROOT
void readData(string path)
{
	//open file for reading
	ifstream in_file;
	in_file.open(path.c_str());
	TNtuple* data = new TNtuple("data", "data from csv file", "V:t"); //create TNtuple with Voltage and time variables
	data->SetDirectory(0); //unlink data from any directory (helps avoid segmentation faults since TFile is create after TNtuple)
	TFile* saveData = new TFile("csv_data.root", "RECREATE"); //make .root file to store new usable data from file
	//use these vectors (for expandable data sets) and strings to store data from file temporarily
	vector<float> V = {};
	vector<float> t = {};
	string values,Vs,ts;
  
//parse through lines of file and save it to the values string
	while(getline(in_file,values))
	{
		//cut the line into the proper segments and save to variables
		ts = values.substr(0,values.find(","));
		Vs = values.substr(values.find(",")+1, values.length());
		//convert string to float and save to vectors
		try{
			V.push_back(stof(Vs));
			t.push_back(stof(ts));
		} catch(...) {}
	}
  
	//parse through vectors and fill TNtuple with entries
	for(int i = 0; i < V.size(); i++)
	{    
		data->Fill(V[i],t[i]);
	}
  
	in_file.close(); //c++ way to close .txt file
	data->Write(); //write TNtuple to .root file
	saveData->Close(); //close .root file after writing

	//delete pointers
	delete data;
	delete saveData;
}


//make histogram (generate waveform) of data from file
void makeHist(string name, string path = "csv_data.root")
{
	TFile in_file(path.c_str()); //read in .root file
	TNtuple* data; //initialize TNtuple with no information
	in_file.GetObject("data", data); //save TNtuple from file to previously initialized TNtuple
	int entries = data->GetEntries();
	TH1F* hist = new TH1F(name.c_str(), name.c_str(), entries, 0, entries); //generated empty histogram
	float V,t;

	//set variables to corresponding entries in TNtuple
	data->SetBranchAddress("V", &V);
	data->SetBranchAddress("t", &t);

	//parse through TNtuple and fill histogram with time data
	int bins = hist->GetNbinsX();
	for(int i = 1; i < entries-1; i++)
	{
		data->GetEntry(i);
		hist->Fill(t);
	}

	//fill histogram bins with the voltage data corresponding to the time data
	for(int i = 0; i < bins; i++)
	{
	  data->GetEntry(i);
		
		if(!hist->IsBinUnderflow(i) && !hist->IsBinOverflow(i)) //ignore under-/over-flow bins
		{
			hist->SetBinContent(i,V);
		}
	}

	TFile* temp = new TFile("temp.root", "RECREATE");
	hist->Write();
	temp->Close();

	//unlink histogram from any directory and save it to .root file
	hist->SetDirectory(0);
	hist->SetStats(0); //do not display stats box (it gets annoying here)
	useWaveformFile(name, "temp.root");    

	//delete pointers
	delete hist;
	delete data;
	delete temp;
}


//gets baseline of waveform for some histogram
double getBaseline(string name, string path)
{
	//load in from .root file and get some histogram
	TFile f_hist(path.c_str());
	TH1F* hist = (TH1F*)f_hist.Get(name.c_str());

	//get number of bins, create a counter, and initialize variable for baseline value
	int bins = hist->GetNbinsX();
	int bin_num;
	double avg = 0;

	//loop through bins of histogram and add all heights to avg
	for(int i = 1; i < bins-1; i++)
	{
		//ignores under-/over-flow bins
		bin_num = hist->GetXaxis()->FindBin(i);
		avg += hist->GetBinContent(bin_num);
	}

	//compute average height of waveform
	avg /= bins;

	//delete pointers and return baseline value
	delete hist;
	return avg;
}


//gets standard deviation of waveform baseline for some histogram
double getStdDev(string name, string path, float avg)
{
	//load in from .root file and get some histogram
	TFile f_hist(path.c_str());
	TH1F* hist = (TH1F*)f_hist.Get(name.c_str());

	//get number of bins, create a counter, and initialize variable for standard deviation (and other incident variables)
	int bins = hist->GetNbinsX();
	int bin_num;
	double std_dev;
	double dx2;
	double xi;

	//loop through bins and calculated (xi - avg)^2
	for(int i = 1; i < bins-1; i++)
	{
		//ignores under-/over-flow bins
		bin_num = hist->GetXaxis()->FindBin(i);
		xi = hist->GetBinContent(bin_num);
		dx2 += pow(xi - avg, 2);
	}

	//calculates standard deviation, deletes pointers, and returns std_dev
	std_dev = sqrt(dx2/bins);
	delete hist;
	return std_dev;
}


//get stats about signal from waveform of any given file path
void examineWaveform(string path)
{
	TFile f_hist(path.c_str()); //load in .root file
	TIter next(f_hist.GetListOfKeys()); //create iterator of keys within .root file
	TKey* key; //creates blank key to be used later
	TNtuple* peaks = new TNtuple("peaks", "stats of signal peaks", "n:x:y:w:h"); //creates TNtuple with x,y,width,height variables
	TNtuple* waveform = new TNtuple("waveform", "waveform attributes", "n:b:s");
	string name; //for name of certain histogram
	TH1F* hist; //temporary histogram
	TNtuple* num_peaks = new TNtuple("num_peaks", "number of peaks per waveform", "p"); //creates TNtuple to save number of peaks per waveform
	int num; //number of peaks in certain waveform

	useWaveformFile("waveform_attributes.root"); //create cumulative file for each waveform attribute

	//loops through keys in .root file
	while((key = (TKey*)next()))
	{
		//save histogram from file to hist and gets name of histogramn (note the type-casting)
		hist = (TH1F*)key->ReadObj();
		name = (string)key->GetName();

		//sets the threshold values for the waveform
		double baseline = getBaseline(name, path.c_str());
		double rms_noise = getStdDev(name, path.c_str(), baseline);
		double threshold = Abs(rms_noise*4);
		double w_threshold = Abs(rms_noise*2.5);
		double ideal_peak = 1; //to see if a peak isn't as high as we want

		//initializes the variables used throughout the waveform analysis
		int bins = hist->GetNbinsX();
		int bin_num;
		double y_values;
		double y_lag;
		double x_values;
		double x_lag;
		double y_crit = 0;
		double x_crit = 0;
		double y_max = baseline;
		double peak_height = 0;
		double width1 = 0,width2 = 0,swidth = 0;
		int check1 = 0;
		num = 0;
		bool check2 = true;

		/* Algorithm for analyzing waveforms:
		//  -loop through all bins excluding under-/over-flow bins
		//  -get current and previous x- and y-values
		//  -check if above w_threshold to start width counter
		//  -check if maximum value and save info to x_crit and y_crit
		//  -check for end of signal
		//  -save peak height, width, and x- and y-values
		//  -reset peak variables
		//  -save number of peaks per waveform to TNtuple
		//  -reset waveform variables
		//  -delete reusable pointers
		//  -repeat loop for all waveforms in file
		*/

		for(int i = 1; i < bins-1; i++)
		{
			bin_num = hist->GetXaxis()->FindBin(i);
			y_values = hist->GetBinContent(bin_num);
			x_values = hist->GetBinCenter(bin_num);

			if(i > 0)
			{
				y_lag = hist->GetBinContent(bin_num-1);
				x_lag = hist->GetBinCenter(bin_num-1);
			}

			if(Abs(y_lag - baseline) < w_threshold && check1 == 0 && Abs(y_values - baseline) > w_threshold)
			{
				width1 = x_values;
				check1 = 1;
			}

			if(Abs(y_values - baseline) > threshold)
			{
				if(Abs(y_lag - baseline) > Abs(y_max - baseline))
				{
					y_max = y_lag;
					if(Abs(y_values	- baseline) < Abs(y_max - baseline))
					{	
						if(!hist->IsBinUnderflow(i) && !hist->IsBinOverflow(i))
						{
							y_crit = y_lag;
							x_crit = x_lag;
						}
					}
				}
			}
			if(Abs(y_lag - baseline) > w_threshold && Abs(y_values - baseline) < w_threshold && check1 == 1)
			{
				width2 = x_lag;
				swidth = width2 - width1;
				if(swidth != 0 && swidth > 15)
				{
					if(y_crit != 0)
					{
						peak_height = Abs(y_crit - baseline);
						num += 1;
						peaks->SetDirectory(0);
						peaks->Fill((float)num, x_crit,y_crit,swidth,peak_height);
						check2 = false;
					}
				}
				
				check1 = 0;
				y_max = baseline;
			}
		}
		
		if(check2)
		{
			peaks->SetDirectory(0);
			peaks->Fill((float)num,x_crit,y_crit,swidth,peak_height);
			check2 = false;
		}

		num_peaks->Fill(num);
		if(peak_height == 0 || num == 0)
		{
			if(num_peaks == 0)
			{
				std::cout << "No peaks in waveform!\t" << name << endl;
				saveHist(name, path, "Time (#mus)", "Voltage (V)", 0.4, 632);
			}

			if(peak_height < ideal_peak)
			{
				std::cout << "Peak not high enough!" << "\tHeight: " << peak_height << "\n" << name << endl;
				saveHist(name, path, "Time (#mus)", "Voltage (V)", 0.4, 632);
			}
		}
		else
		{
			saveHist(name, path, "Time (#mus)", "Voltage (V)");
		}
		waveform->Fill((float)num, (float)baseline, (float)rms_noise);

		delete hist;
	}
  
	//unlink waveform attributes TNtuple from any directory and save to .root file
	waveform->SetDirectory(0);
	TFile waveform_file("waveform_attributes.root", "RECREATE");
	waveform->Write();
	waveform_file.Close();

	//unlink peak statistics TNtuple from any directory and save to .root file
	peaks->SetDirectory(0);
	TFile out_file("signal_stats.root", "RECREATE");
	peaks->Write();
	out_file.Close();

	//unlink number of peaks per waveform TNtuple from any directory and save to .root file
	num_peaks->SetDirectory(0);
	TFile num_file("num_peaks.root", "RECREATE");
	num_peaks->Write();
	num_file.Close();

	//delete pointers
	delete key;
	delete peaks;
	delete num_peaks;
	delete waveform;
}


//make distribution of heights of peaks in multiple waveforms
void peakDistro()
{
	//load in from .root file and get TNtuple with peak statistics
	TFile in_file("signal_stats.root");
	TNtuple* peaks;
	in_file.GetObject("peaks", peaks);

	//create blank histogram and related variables
	int entries = peaks->GetEntries();
	TH1F* peak_distro = new TH1F("peaks", "peaks distribution", entries, 0, 400);
	float peak_height;

	//connect variable to corresponding TNtuple
	peaks->SetBranchAddress("h", &peak_height);

	//loop through TNtuple and fill histogram
	for(int i = 0; i < entries; i++)
	{
		peaks->GetEntry(i);
		peak_distro->Fill(peak_height);
	}

	//unlink TNtuple from any directory and save to .root file
	peaks->SetDirectory(0);
	TFile out_file("peaks_distro.root", "RECREATE");
	peak_distro->Write();
	out_file.Close();

	//set up canvas, draw histogram, and save to .gif file
	TCanvas canvas("canvas", "height distro canvas");  
	peak_distro->Draw();
	canvas.SaveAs("peaks_histogram.gif");

	//delete pointers
	delete peaks;
	delete peak_distro;
}


//make distribution of number of peaks in multiple waveforms
void numPeakDistro()
{
	//load in from .root file and get TNtuple with number of peaks per waveform
	TFile in_file("num_peaks.root");
	TNtuple* peaks;
	in_file.GetObject("num_peaks", peaks);

	//create blank histogram and related variables
	int entries = peaks->GetEntries();
	TH1F* peak_distro = new TH1F("num_peaks", "peak number distribution", 100, 0, 5);
	float num_peak;

	//connect variable to corresponding TNtuple
	peaks->SetBranchAddress("p", &num_peak);

	//loop through TNtuple and fill histogram
	for(int i = 0; i < entries; i++)
	{
		peaks->GetEntry(i);
		peak_distro->Fill(num_peak);
	}

	//set up canvas, draw histogram, and save to .gif file
	TCanvas canvas("canvas", "height distro canvas");
	peak_distro->Draw();
	canvas.SaveAs("num_peaks_histogram.gif");

	//delete pointers
	delete peaks;
	delete peak_distro;
}


//saves individual FFT of noise and takes its name and host path as an input
void saveFFT(TH1F* noise, string name)
{
	//initialize blank variables/objects for use later
	//TH1F* noise;
	int N;
	int bin_num;
	TVirtualFFT* fft;

	//noise = (TH1F*)f_hist->Get(name.c_str()); //get waveform (note type-casting and .c_str() (string to char*))
	TVirtualFFT::SetTransform(0); //reset transformation just in case
	N = noise->GetNbinsX(); //get number of x-values
	fft = TVirtualFFT::FFT(1, &N, "R2C EX K"); //set up FFT with 1 dimension, N x-values, and certain FFT properties
	double values[N-2]; //for y-values of fft object

	//loop through bins of waveform histogram
	for(int i = 1; i < N-1; i++)
	{
		bin_num = noise->GetXaxis()->FindBin(i);
		values[i] = (double)noise->GetBinContent(bin_num); //note type-casting
	}

	//set y-values of transformation, load transformation, perform transformation on noise, save to noise
	fft->SetPoints(values);
	fft->Transform();
	noise = (TH1F*)TH1::TransformHisto(fft,noise,"MAG");
	noise->SetMaximum(350); //set y-axis maximum

	noise->SetDirectory(0);
	TCanvas canvas("canvas", "canvas");
	noise->Draw();
	canvas.SaveAs(name.c_str());

	//delete pointers
	delete fft;
}


//loop through waveforms and perform FFT on them
void noiseFFT(string path)
{	
	TFile f_hist(path.c_str()); //load in .root file
	TIter next(f_hist.GetListOfKeys()); //create iterator of keys within .root file
	TKey* key; //creates blank key to be used later
	TH1F* hist;
	string name; //for name of certain histogram

	//loops through keys in .root file
	while((key = (TKey*)next()))
	{
		name = (string)key->GetName(); //sets name (variable) to name of key (aka name of the waveform/histogram)
		hist = (TH1F*)f_hist.Get(name.c_str());
		name = name + "FFT.gif";
		hist->SetDirectory(0);
		saveFFT(hist, name); //runs saveFFT with string name as a parameter
	}

	//deletes pointers
	delete key;
}


//generates file and fills it with peaks statistics
void signalStats(string path)
{
	string filename = path + ".csv";
	TFile in_file("signal_stats.root");
	TNtuple* peaks;
	in_file.GetObject("peaks", peaks);

	ofstream out_file;
	out_file.open(filename);

	float n, x, y, w, h;

	peaks->SetBranchAddress("n", &n);
	peaks->SetBranchAddress("x", &x);
	peaks->SetBranchAddress("y", &y);
	peaks->SetBranchAddress("w", &w);
	peaks->SetBranchAddress("h", &h);

	string line;

	for(int i = 0; i < peaks->GetEntries(); i++)
	{
		peaks->GetEntry(i);
		line = to_string(int(n)) + "," + to_string(x) + "," + to_string(y) + "," + to_string(w) + "," + to_string(h);
		out_file << line << '\n';
	}

	delete peaks;
}


//generates file and fills it with waveform attributes
void waveformAttributes(string path)
{
	string filename = path + ".csv";
	TFile in_file("waveform_attributes.root");
	TNtuple* waveform;
	in_file.GetObject("waveform", waveform);

	ofstream out_file;
	out_file.open(filename);

	float n, b, s;

	waveform->SetBranchAddress("b", &b);
	waveform->SetBranchAddress("n", &n);
	waveform->SetBranchAddress("s", &s);
	
	string line;

	for(int i = 0; i < waveform->GetEntries(); i++)
	{
		waveform->GetEntry(i);
		line = to_string(int(n)) + "," + to_string(b) + "," + to_string(s);
		out_file << line << '\n';
	}

	delete waveform;
}


//empty
int main()
{
  return 0;
}
