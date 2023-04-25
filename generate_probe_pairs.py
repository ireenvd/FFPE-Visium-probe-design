"""
This script takes an output file from primer3 command line version as input file and generates a probe pair from it.
The probes generated by primer3 function ars potential LHS probes. 

In each sequence object, multiple probe pair objects are stored containing the following information: 
- Left hand side (LHS) and Right hand side (RHS) ID
- Probe pair start site
- Probe pair end site 
- LHS and RHS sequence
- LHS and RHS GC percentage. NOTE: this is only of the hybridising part, so it does not include the probe handle in the calculation 

For each sequence, this script: 
- selects the left hand side probes which end at a T nucleotide, as instructed in 10X Genomics guidelines for probe design. 
- expands the probe 25 nucleotides starting from this T to the right to build a 25 nt long RHS probe 
- adds the probe handles to both LHS nad RHS probes 
- orders and indexes the probes based on their start site on the template sequence
- removes probes of which the RHS GC content percentage does not fall within the range of 44 - 72 
- removes probes which would "fall off" the sequence template 
- generates a file suitable to use with IDT OligoAnalyzer batch format

to be tested outside of this script:
- overlap of probes
- self complementarity 
- off target hybridisation 

LHS probe template: 5’-CCTTGGCACCCGAGAATTCCA-target_LHS-3’ 
RHS probe template: /5Phos/-target_RHS-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA-3’

"""

## import packages 
from Bio.SeqUtils import gc_fraction
from Bio.Seq import Seq
import os 

## define the class Probe 
class Probe:
    def __init__(self):
        self.RHS_ID = "" #ID of RHS probe
        self.LHS_ID = "" #ID of LHS probe 
        self.START = 0 #index of first nucleotide of LHS probe on sequence template 
        self.END = 0 #index of last nucleotide of RHS probe on sequence template
        self.LHS = "" #left hand side sequence
        self.LHS_GC = 0 #left hand side GC percentage
        self.RHS = "" #right hand side sequence
        self.RHS_GC = 0 #right hand side GC content

## define the class Sequence 
class Sequence:
    def __init__(self):
        self.ID = "" #sequence ID 
        self.TEMPLATE = "" #sequence template 
        self.PROBES = [] #probes belonging to that sequence 

## generate the RHS probe based on the LHS probe 
def create_rhs(Sequence, Probe):
    my_dna = Seq(Sequence.TEMPLATE)
    RHS_start = int(Probe.START) + 25
    RHS_end = int(RHS_start) + 25
    RHS_seq = my_dna[RHS_start:RHS_end] #do not take complement, as input is DNA sequence rather than RNA sequence
    RHS_GC = str(format(float(gc_fraction(RHS_seq)*100), '.3f')) #3 decimal places. Convert to string to allow for concatanation in printer function. 
    RHS = str(RHS_seq) + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" #add probe handle
    return RHS, RHS_GC, str(RHS_end)

## printer function 
def printer(Sequences):
    for sequence in Sequences:
        print("/-------------------/")
        print("Sequence id: " + sequence.ID)
        print("Sequence template:\n" + sequence.TEMPLATE + "\n")
        print("Probes: \n")
        for probe in sequence.PROBES:
            print("     probe pair LHS ID: " + probe.LHS_ID)
            print("     probe pair RHS ID: " + probe.RHS_ID)
            print("     probe pair START: " + probe.START)
            print("     probe pair END: " + probe.END)
            print("     probe LHS: " + probe.LHS)
            print("     probe LHS GC: " + probe.LHS_GC)
            print("     probe RHS: " + probe.RHS)
            print("     probe RHS GC: " + probe.RHS_GC)
            print("     -----------------\n")

## Created by Ireen van Dolderen all rights reserved
def process():
    file1 = open('primer3_output.txt', 'r')
    Lines = file1.readlines()
    sequences = []
    new_sequence = Sequence()
    new_probe = Probe()
    probe_collection_mode = False
    for line in Lines:
        if line == "=\n": #= indicates the end of a sequence query in primer3 output
            i = 0 
            for probe in new_sequence.PROBES: 
                probe.LHS_ID = str(new_sequence.ID+"_LHS_"+str(i)) #write probe ID for left hand side 
                probe.RHS_ID = str(new_sequence.ID+"_RHS_"+str(i)) #write probe ID for right hand side 
                i = i + 1 
            sequences.append(new_sequence)
            new_sequence = Sequence()
        information = line.split('=')
        information[0] = ''.join([i for i in information[0] if not i.isdigit()]) #remove number from left hand sides to allow iteration over all primers
        information[1] = information[1].replace('\n', '')
        if information[0] == "SEQUENCE_ID":
            new_sequence.ID = information[1] #add template sequence ID 
        if information[0] == "SEQUENCE_TEMPLATE":
            new_sequence.TEMPLATE = information[1] #add template sequence 

        ## start probe collection into sequence instance 
        if information[0] == "PRIMER_INTERNAL__SEQUENCE":
            if information[1][-1] == 'T':
                new_probe.LHS = "CCTTGGCACCCGAGAATTCCA" +information[1] #add probe handle 
                probe_collection_mode = True #only add probe to sequence object if last nucleotide of the probe is a T 
        if information[0] == "PRIMER_INTERNAL_" and probe_collection_mode is True:
            new_probe.START = information[1].split(',')[0] 
        if information[0] == "PRIMER_INTERNAL__GC_PERCENT" and probe_collection_mode is True:
            new_probe.LHS_GC = information[1]
            new_probe.RHS, new_probe.RHS_GC, new_probe.END = create_rhs(new_sequence, new_probe) #call RHS function 
            new_sequence.PROBES.append(new_probe)
            new_probe = Probe()
            probe_collection_mode = False
        
        ## delete a probe pair if the GC content of the RHS probe does not fall in the range of 44 - 72 
        for i, probe in enumerate(new_sequence.PROBES): 
            if float(probe.RHS_GC) < 44 or float(probe.RHS_GC) > 72: 
                del new_sequence.PROBES[i]
                break
        
        ## delete probe pair if the RHS probe "falls off" the sequence template 
        for i, probe in enumerate(new_sequence.PROBES):
            if int(probe.END) > len(new_sequence.TEMPLATE):
                del new_sequence.PROBES[i]
                break 
        
        ## sort probes based on index on template sequence 
        new_sequence.PROBES.sort(key = lambda x : int(x.START)) 
    return sequences


if __name__ == "__main__":
    sequences = process()
    printer(sequences)        



### OBS multiple writing options. Comment out which one you do not need

## write one file per sequence containing the probe pairs in IDT OligoAnalyzer batch format 
if __name__ == "__main__":
    sequences = process()
    os.chdir("idt_files")
    for sequence in sequences: 
        f = open(str(sequence.ID)+"_probeseqs.txt", "w") 
        for probe in sequence.PROBES:
            f.write(probe.LHS_ID+"\t"+probe.LHS+"\n")
            f.write(probe.RHS_ID+"\t"+probe.RHS+"\n")
        f.close()
    os.chdir("../")


## write one fasta file containing all the LHS and RHS combined, hybridising sequences. 
## Purpose: test for off target hybridisation  
fasta = open("probe_pairs_hyb_comb_T89.fasta", "w")
if __name__ == "__main__":
    sequences = process()
    for sequence in sequences: 
        for probe in sequence.PROBES:
            hyb_LHS = probe.LHS[-25:] #only take the hybrdising part of the probe, i.e. the last 25 nucleotides    
            hyb_RHS = probe.RHS[:25] #only take the hybridising part of the probe, i.e. the first 25 nucleotides 
            fasta.write(">"+probe.LHS_ID+"\n"+hyb_LHS+hyb_RHS+"\n") #the LHS ID is kept for writing convenience. The sequence is the probe pair 

            # # write only the hybridising parts, but LHS and RHS individually 
            # hyb_LHS = probe.LHS[-25:] #only take the hybrdising part of the probe, i.e. the last 25 nucleotides    
            # hyb_RHS = probe.RHS[:25] #only take the hybridising part of the probe, i.e. the first 25 nucleotides. 
            # fasta.write(">"+probe.LHS_ID+"\n"+hyb_LHS+"\n")
            # fasta.write(">"+probe.RHS_ID+"\n"+hyb_RHS+"\n")

            # # write the full probes including handles, LHS and RHS individually 
            # fasta.write(">"+probe.LHS_ID+"\n"+probe.LHS+"\n")
            # fasta.write(">"+probe.RHS_ID+"\n"+probe.RHS+"\n")
fasta.close()


## write one fasta file per sequence containing all probes for that sequence 
## only include the hybridising parts of the probes 
if __name__ == "__main__":
    sequences = process()
    os.chdir("probe_fasta_files")
    for sequence in sequences: 
        f = open(str(sequence.ID)+"_probeseqs.fasta", "w") 
        for probe in sequence.PROBES:
            hyb_LHS = probe.LHS[-25:] #only take the hybrdising part of the probe, i.e. the last 25 nucleotides    
            hyb_RHS = probe.RHS[:25] #only take the hybridising part of the probe, i.e. the first 25 nucleotides 
            f.write(">"+probe.LHS_ID+"\n"+hyb_LHS+"\n")
            f.write(">"+probe.RHS_ID+"\n"+hyb_RHS+"\n")
        f.close()
    os.chdir("../") 
