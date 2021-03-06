#BEGIN_HEADER

import simplejson
import sys
import shutil
import os
import ast
import glob
import json
import uuid
import logging
import time
import subprocess
import threading, traceback
import multiprocessing
from collections import OrderedDict
from pprint import pprint,pformat
import script_util
from biokbase.workspace.client import Workspace
import handler_utils as handler_util
from biokbase.auth import Token
from mpipe import OrderedStage , Pipeline
import multiprocessing as mp
import re
import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()

try:
    from biokbase.HandleService.Client import HandleService
except:
    from biokbase.AbstractHandle.Client import AbstractHandle as HandleService

_KBaseRNASeq__DATA_VERSION = "0.2"

class KBaseRNASeqException(BaseException):
	def __init__(self, msg):
		self.msg = msg
	def __str__(self):
		return repr(self.msg)


#END_HEADER


class KBaseRNASeq:
    '''
    Module Name:
    KBaseRNASeq

    Module Description:
    
    '''

    ######## WARNING FOR GEVENT USERS #######
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    #########################################
    #BEGIN_CLASS_HEADER
    __TEMP_DIR = 'temp'
    __BOWTIE_DIR = 'bowtie'
    __BOWTIE2_DIR = 'bowtie2'
    __GTF_DIR = 'gtfdir'
    __TOPHAT_DIR = 'tophat'
    __CUFFLINKS_DIR = 'cufflinks'
    __CUFFMERGE_DIR = 'cuffmerge'
    __CUFFDIFF_DIR = 'cuffdiff'
    __PUBLIC_SHOCK_NODE = 'true'
    __ASSEMBLY_GTF_FN = 'assembly_GTF_list.txt'
    __STATS_DIR = 'stats'
    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
	 # This is where config variable for deploy.cfg are available
        #pprint(config)
        if 'ws_url' in config:
              self.__WS_URL = config['ws_url']
        if 'shock_url' in config:
              self.__SHOCK_URL = config['shock_url']
	if 'hs_url' in config:
	      self.__HS_URL = config['hs_url']
        if 'temp_dir' in config:
              self.__TEMP_DIR = config['temp_dir']
	if 'scratch' in config:
	      self.__SCRATCH= config['scratch']
        if 'bowtie_dir' in config:
              self.__BOWTIE_DIR = config['bowtie_dir']
        if 'genome_input_fa' in config:
              self.__GENOME_FA = config['genome_input_fa']
        if 'svc_user' in config:
              self.__SVC_USER = config['svc_user']
        if 'svc_pass' in config:
              self.__SVC_PASS = config['svc_pass']
	if 'scripts_dir' in config:
	      self.__SCRIPTS_DIR = config['scripts_dir']
	if 'force_shock_node_2b_public' in config: # expect 'true' or 'false' string
	      self.__PUBLIC_SHOCK_NODE = config['force_shock_node_2b_public']
	
	self.__SCRIPT_TYPE = { 'ContigSet_to_fasta' : 'ContigSet_to_fasta.py',
			  	'RNASeqSample_to_fastq' : 'RNASeqSample_to_fastq',
			  	'cufflinks' : 'cufflinks',
				'tophat_script' : 'Tophat_pipeline.py'
			     } 

        # logging
        self.__LOGGER = logging.getLogger('KBaseRNASeq')
        if 'log_level' in config:
              self.__LOGGER.setLevel(config['log_level'])
        else:
              self.__LOGGER.setLevel(logging.INFO)
        streamHandler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s - %(filename)s - %(lineno)d - %(levelname)s - %(message)s")
        formatter.converter = time.gmtime
        streamHandler.setFormatter(formatter)
        self.__LOGGER.addHandler(streamHandler)
        self.__LOGGER.info("Logger was set")

        #END_CONSTRUCTOR
        pass

    def fastqcCall(self, ctx, params):
        # ctx is the context object
        # return variables are: job_id
        #BEGIN fastqcCall
        #END fastqcCall

        # At some point might do deeper type checking...
        if not isinstance(job_id, basestring):
            raise ValueError('Method fastqcCall return value ' +
                             'job_id is not type basestring as required.')
        # return the results
        return [job_id]

    def associateReads(self, ctx, params):
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN associateReads
	user_token=ctx['token']
        ws_client=Workspace(url=self.__WS_URL, token=user_token)
	out = dict()
	out['metadata'] = { k:v for k,v in params.iteritems() if not k in ('ws_id', "analysis_id", "genome_id","singleend_sample","pairedend_sample") and v is not None }
	self.__LOGGER.info( "Uploading RNASeqSample {0}".format(out['metadata']['sample_id']))
	if "genome_id" in params and params['genome_id'] is not None:
	    out["metadata"]["genome_id"] = script_util.get_obj_info(self.__LOGGER,self.__WS_URL,[params["genome_id"]],params["ws_id"],user_token)[0]
	if "analysis_id" in params and params['analysis_id'] is not None:
            g_ref = script_util.get_obj_info(self.__LOGGER,self.__WS_URL,[params['analysis_id']],params['ws_id'],user_token)[0]
            out['analysis_id'] = g_ref
	if 'singleend_sample' in params and params['singleend_sample']  is not None:
	    try:
                s_res= ws_client.get_objects(
                                        [{'name' : params['singleend_sample'],
                                          'workspace' : params['ws_id']}])
               	out['singleend_sample'] = s_res[0]['data']
            except Exception,e:
                raise KBaseRNASeqException("Error Downloading SingleEndlibrary object from the workspace {0},{1}".format(params['singleend_sample'],e))

	if 'pairedend_sample' in params and params['pairedend_sample']  is not None:
 	    try:
		p_res= ws_client.get_objects(
                                         [{'name' : params['pairedend_sample'],
                                           'workspace' : params['ws_id']}])
                out['pairedend_sample'] = p_res[0]['data']

            except Exception,e:
                raise KBaseRNASeqException("Error Downloading PairedEndlibrary object from the workspace {0},{1}".format(params['pairedend_sample'],e))

	try:
        	res= ws_client.save_objects(
                                {"workspace":params['ws_id'],
                                 "objects": [{
                                                "type":"KBaseRNASeq.RNASeqSample",
                                                "data":out,
                                                "name":out['metadata']['sample_id']}]
                                })
	        returnVal = {"workspace": params['ws_id'],"output" : out['metadata']['sample_id'] }


	except Exception ,e:
		raise KBaseRNASeqException("Error Saving the object to workspace {0},{1} ".format(out['metadata']['sample_id'],e))
	

        #END associateReads

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method associateReads return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

    def SetupRNASeqAnalysis(self, ctx, params):
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN SetupRNASeqAnalysis
	user_token=ctx['token']
        ws_client=Workspace(url=self.__WS_URL, token=user_token)
        out_obj = { k:v for k,v in params.iteritems() if not k in ('ws_id','genome_id','annotation_id', 'tissue', 'condn_labels' , 'singleEnd_reads' , 'pairedEnd_reads') and v}
        if "num_samples" in out_obj : out_obj["num_samples"] = int(out_obj["num_samples"])
        if "num_replicates" in out_obj : out_obj["num_replicates"] = int(out_obj["num_replicates"])
	if "genome_id" in params and params['genome_id'] is not None: out_obj["genome_id"] = script_util.get_obj_info(self.__LOGGER,self.__WS_URL,[params["genome_id"]],params["ws_id"],user_token)[0]
	if "annotation_id" in params and params['annotation_id'] is not None: 
	    g_ref = script_util.get_obj_info(self.__LOGGER,self.__WS_URL,[params['annotation_id']],params['ws_id'],user_token)[0]
	    out_obj['annotation_id'] = g_ref
	if "tissue" in params and params['tissue'] is not None:
	    out_obj['tissue'] = params['tissue'] 
	if "condn_labels" in params and params['condn_labels'] is not None:
            out_obj['condition'] = params['condn_labels']

        self.__LOGGER.info( "Uploading RNASeq Analysis object to workspace {0}".format(out_obj['experiment_id']))
	try:
        	res= ws_client.save_objects(
                                {"workspace":params['ws_id'],
                                 "objects": [{
                                                "type":"KBaseRNASeq.RNASeqAnalysis",
                                                "data":out_obj,
                                                "name":out_obj['experiment_id']}]
                                })
 		returnVal = out_obj
	except Exception,e:
		raise KBaseRNASeqException("Error Saving the object to workspace {0},{1}".format(out_obj['experiment_id'],e))
	self.__LOGGER.info( "Updating  RNASeqSamples associated with the analysis")
	out_obj['sample_ids']= [] 
	exp_id = script_util.get_obj_info(self.__LOGGER,self.__WS_URL,[out_obj['experiment_id']],params['ws_id'],user_token)[0]
	r_obj = { "analysis_id" : exp_id, "metadata" : { "domain" : params['domain'] , "platform" : params['platform'] , "genome_id" : out_obj['genome_id'] } } 
	if "singleEnd_reads" in params and params['singleEnd_reads'] is not None:
		sample_type =  "singleend_sample"
		exp_reads = params['singleEnd_reads']
	elif "pairedEnd_reads" in params and params['pairedEnd_reads'] is not None:
		sample_type =  "pairedend_sample"
		exp_reads = params['pairedEnd_reads']	
	    # Create RNASeqSample obj
	rep_id  =  0
	count = -1
	l_labels = [ [x] * out_obj['num_replicates'] for x in out_obj['condition']]
	#print l_labels
	rep_labels = reduce(lambda x,y: x+y, l_labels)
	#print rep_labels
	for reads in exp_reads:
		count = count + 1
		if int(params['num_replicates']) >= 1: 
	 		rep_id = rep_id + 1	 
			if rep_id > int(params['num_replicates']):
	 			rep_id = 1	 
		s_res = ws_client.get_objects([{'name' : reads,
                                        	'workspace' : params['ws_id']}])
		r_obj['metadata']['sample_id'] = reads+"_RNASeqSample"
		r_obj['metadata']['replicate_id'] = str(rep_id)
		r_obj['metadata']['condition'] = rep_labels[count]
                r_obj[sample_type] = s_res[0]['data']
		samp_obj = ws_client.save_objects( {
                                 "workspace":params['ws_id'],
                                 "objects": [{
                                                "type":"KBaseRNASeq.RNASeqSample",
                                                "data":r_obj,
                                                "name":r_obj['metadata']['sample_id']}]
                                })
		r_sample = script_util.get_obj_info(self.__LOGGER,self.__WS_URL,[r_obj['metadata']['sample_id']],params['ws_id'],user_token)[0]
		out_obj['sample_ids'].append(r_sample)

	self.__LOGGER.info( "Updating  RNASeq Analysis object to workspace {0}".format(out_obj['experiment_id']))
        try:
                res= ws_client.save_objects(
                                {"workspace":params['ws_id'],
                                 "objects": [{
                                                "type":"KBaseRNASeq.RNASeqAnalysis",
                                                "data":out_obj,
                                                "name":out_obj['experiment_id']}]
                                })
	except Exception,e:
                raise KBaseRNASeqException("Error Updating the object to workspace {0},{1}".format(out_obj['experiment_id'],e))
                #returnVal = {"workspace": params['ws_id'],"output" : out_obj['experiment_id'] }
        returnVal = out_obj

        #END SetupRNASeqAnalysis

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method SetupRNASeqAnalysis return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

    def BuildBowtie2Index(self, ctx, params):
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN BuildBowtie2Index
	user_token=ctx['token']
   	#pprint(params) 
        #svc_token = Token(user_id=self.__SVC_USER, password=self.__SVC_PASS).token
        ws_client=Workspace(url=self.__WS_URL, token=user_token)
	hs = HandleService(url=self.__HS_URL, token=user_token)
	try:
	        self.__LOGGER.info( "Downloading ContigSet object from workspace")
	    ## Check if the bowtie_dir is present; remove files in bowtie_dir if exists ; create a new dir if doesnt exists
		#if os.path.exists(self.__SCRATCH):
		#   shutil.rmtree(self.__SCRATCH)
		#os.makedirs(self.__SCRATCH)
	   	if not os.path.exists(self.__SCRATCH): os.makedirs(self.__SCRATCH)
	    	bowtie_dir = self.__SCRATCH + '/tmp' 
	    	if os.path.exists(bowtie_dir):
			handler_util.cleanup(self.__LOGGER,bowtie_dir)
	   	if not os.path.exists(bowtie_dir): os.makedirs(bowtie_dir)
	     	provenance = [{}]
        	if 'provenance' in ctx:
            		provenance = ctx['provenance']
        	# add additional info to provenance here, in this case the input data object reference
        	provenance[0]['input_ws_objects']=[params['ws_id']+'/'+params['reference']]
		ref_info = ws_client.get_object_info_new({"objects": [{'name': params['reference'], 'workspace': params['ws_id']}]})
		if ref_info[0][2].split('-')[0] == 'KBaseGenomes.Genome':
			ref = ws_client.get_objects([{'name': params['reference'], 'workspace': params['ws_id']}])
			contig_set = ref[0]['data']['contigset_ref']
			#print contig_set
			c_ws = str(contig_set.split('/')[0])
			obj_id  = str(contig_set.split('/')[1])
			obj_version_number = str(contig_set.split('/')[1])
			#print c_ws + "\t" + obj_id
			if params['reference'].split('.')[-1] not in ['fa','fasta','fna']:
                                outfile_ref_name = params['reference']+".fa"
                                dumpfasta= "--workspace_service_url {0} --workspace_name {1} --working_directory {2} --output_file_name {3} --object_reference {4} --shock_service_url {5} --token \'{6}\'".format(self.__WS_URL ,c_ws,bowtie_dir,outfile_ref_name,contig_set,self.__SHOCK_URL,user_token)
	        else:   		
	   ## dump fasta object to a file in bowtie_dir
		    #try:
		 	if params['reference'].split('.')[-1] not in ['fa','fasta','fna']:
				outfile_ref_name = params['reference']+".fa"
	   			dumpfasta= "--workspace_service_url {0} --workspace_name {1} --working_directory {2} --output_file_name {3} --object_name {4} --shock_service_url {5} --token \'{6}\'".format(self.__WS_URL , params['ws_id'],bowtie_dir,outfile_ref_name,params['reference'],self.__SHOCK_URL,user_token)
			else:
			      	outfile_ref_name = params['reference']
			  	dumpfasta= "--workspace_service_url {0} --workspace_name {1} --working_directory {2} --output_file_name {3} --object_name {4} --shock_service_url {5} --token \'{6}\'".format(self.__WS_URL , params['ws_id'],bowtie_dir,params['reference'],params['reference'],self.__SHOCK_URL,user_token)
                try: 
			script_util.runProgram(self.__LOGGER,self.__SCRIPT_TYPE['ContigSet_to_fasta'],dumpfasta,self.__SCRIPTS_DIR,os.getcwd())
		except Exception,e:
			raise KBaseRNASeqException("Error Creating  FASTA object from the workspace {0},{1},{2}".format(params['reference'],os.getcwd(),e))
		 
	   
	    ## Run the bowtie_indexing on the  command line
		try:
	    		if outfile_ref_name:
				bowtie_index_cmd = "{0} {1}".format(outfile_ref_name,params['reference'])
			else:
				bowtie_index_cmd = "{0} {1}".format(params['reference'],params['reference']) 
	    	        self.__LOGGER.info("Executing: bowtie2-build {0}".format(bowtie_index_cmd))  	
			cmdline_output = script_util.runProgram(self.__LOGGER,"bowtie2-build",bowtie_index_cmd,None,bowtie_dir)
			if 'result' in cmdline_output:
				report = cmdline_output['result']
		except Exception,e:
			raise KBaseRNASeqException("Error while running BowtieIndex {0},{1}".format(params['reference'],e))
		
	    ## Zip the Index files
		try:
			script_util.zip_files(self.__LOGGER, bowtie_dir,os.path.join(self.__SCRATCH ,"%s.zip" % params['output_obj_name']))
			out_file_path = os.path.join(self.__SCRATCH,"%s.zip" % params['output_obj_name'])
        	except Exception, e:
			raise KBaseRNASeqException("Failed to compress the index: {0}".format(e))
	    ## Upload the file using handle service
		try:
			#bowtie_handle = script_util.create_shock_handle(self.__LOGGER,"%s.zip" % params['output_obj_name'],self.__SHOCK_URL,self.__HS_URL,"Zip",user_token)	
			bowtie_handle = hs.upload(out_file_path)
			# if self.__PUBLIC_SHOCK_NODE is 'true': 
                	# 	script_util.shock_node_2b_public(self.__LOGGER,node_id=bowtie_handle['id'],shock_service_url=bowtie_handle['url'],token=user_token)
			 
		except Exception, e:
			raise KBaseRNASeqException("Failed to upload the Zipped Bowtie2Indexes file: {0}".format(e))
	    	bowtie2index = { "handle" : bowtie_handle ,"size" : os.path.getsize(out_file_path)}   

	     ## Save object to workspace
	   	self.__LOGGER.info( "Saving bowtie indexes object to  workspace")
	   	res= ws_client.save_objects(
					{"workspace":params['ws_id'],
					 "objects": [{
					 "type":"KBaseRNASeq.Bowtie2Indexes",
					 "data":bowtie2index,
					 "name":params['output_obj_name']}
					]})
	    	#returnVal = { "output" : params['output_obj_name'],"workspace" : params['ws_id'] }
		info = res[0]
	     ## Create report object:
                reportObj = {
                                'objects_created':[{
                                'ref':str(info[6]) + '/'+str(info[0])+'/'+str(info[4]),
                                'description':'Build Bowtie2 Index'
                                }],
                                'text_message':report
                            }

             # generate a unique name for the Method report
                reportName = 'Build_Bowtie2_Index_'+str(hex(uuid.getnode()))
                report_info = ws_client.save_objects({
                                                'id':info[6],
                                                'objects':[
                                                {
                                                'type':'KBaseReport.Report',
                                                'data':reportObj,
                                                'name':reportName,
                                                'meta':{},
                                                'hidden':1, # important!  make sure the report is hidden
                                                'provenance':provenance
                                                }
                                                ]
                                                })[0]

       	 	print('saved Report: '+pformat(report_info))
			
	    	returnVal = { "report_name" : reportName,"report_ref" : str(report_info[6]) + '/' + str(report_info[0]) + '/' + str(report_info[4]) }
	except Exception, e:
		raise KBaseRNASeqException("Build Bowtie2Index failed: {0}".format(e))
	finally:
                handler_util.cleanup(self.__LOGGER,bowtie_dir)
		#if os.path.exists(out_file_path): os.remove(out_file_path)
        #END BuildBowtie2Index

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method BuildBowtie2Index return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

    def GetFeaturesToGTF(self, ctx, params):
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN GetFeaturesToGTF
        user_token=ctx['token']
        #pprint(params)
        ws_client=Workspace(url=self.__WS_URL, token=user_token)
        hs = HandleService(url=self.__HS_URL, token=user_token)
        try:
                self.__LOGGER.info( "Downloading Genome object from workspace")
            ## Check if the gtf_dir is present; remove files in gtf_dir if exists ; create a new dir if doesnt exists     
		#if os.path.exists(self.__SCRATCH):
                # 	handler_util.cleanup(self.__LOGGER,self.__SCRATCH)
            	if not os.path.exists(self.__SCRATCH): os.makedirs(self.__SCRATCH)
		gtf_dir = self.__SCRATCH+'/tmp'
                if os.path.exists(gtf_dir):
                        handler_util.cleanup(self.__LOGGER,gtf_dir)
                if not os.path.exists(gtf_dir): os.makedirs(gtf_dir)
                provenance = [{}]
                if 'provenance' in ctx:
                        provenance = ctx['provenance']
                # add additional info to provenance here, in this case the input data object reference
                provenance[0]['input_ws_objects']=[params['ws_id']+'/'+params['reference']]
		out_file_path = os.path.join(gtf_dir,params['output_obj_name']+'.gtf')
		output = open(out_file_path,'w')
		try:	
                	reference = ws_client.get_object_subset(
                                        [{ 'name' : params['reference'], 'workspace' : params['ws_id'],'included': ['features']}])
                	#reference = ws_client.get_objects(
                        #                [{ 'name' : params['reference'], 'workspace' : params['ws_id']}])
			ref =reference[0]['data']
        		if "features" in ref:
                  		for f in ref['features']:
                     			if "type" in f and  f['type'] == 'CDS': f_type = f['type']
                     			if "id" in f: f_id =  f['id']
                     			if "location" in f:
                        			for contig_id,f_start,f_strand,f_len  in f['location']:
                                			f_end = script_util.get_end(int(f_start),int(f_len),f_strand)
			        			output.write(contig_id + "\tKBase\t" + f_type + "\t" + str(f_start) + "\t" + str(f_end) + "\t.\t" + f_strand + "\t"+ str(0) + "\ttranscript_id " + f_id + "; gene_id " + f_id + ";\n")
		except Exception,e:
			raise KBaseRNASeqException("Failed to create Reference Annotation File: {0}".format(e))	
		finally:
			output.close()
                try:
			#out_file_path = os.path.join(params['output_obj_name']+'.gtf')
                        gtf_handle = hs.upload(out_file_path)

                except Exception, e:
                        raise KBaseRNASeqException("Failed to create Reference Annotation: {0}".format(e))
                gtfhandle = { "handle" : gtf_handle ,"size" : os.path.getsize(out_file_path)}

             ## Save object to workspace
                self.__LOGGER.info( "Saving Reference Annotation object to  workspace")
                res= ws_client.save_objects(
                                        {"workspace":params['ws_id'],
                                         "objects": [{
                                         "type":"KBaseRNASeq.ReferenceAnnotation",
                                         "data":gtfhandle,
                                         "name":params['output_obj_name']}
                                        ]})
                info = res[0]
		report = "Extracting Features from {0}".format(params['reference'])
             ## Create report object:
                reportObj = {
                                'objects_created':[{
                                'ref':str(info[6]) + '/'+str(info[0])+'/'+str(info[4]),
                                'description':'Create Reference Annotation'
                                }],
                                'text_message':report
                            }
                reportName = 'Create_Reference_Annotation_'+str(hex(uuid.getnode()))
                report_info = ws_client.save_objects({
                                                'id':info[6],
                                                'objects':[
                                                {
                                                'type':'KBaseReport.Report',
                                                'data':reportObj,
                                                'name':reportName,
                                                'meta':{},
                                                'hidden':1, # important!  make sure the report is hidden
                                                'provenance':provenance
                                                }
                                                ]
                                                })[0]

                print('saved Report: '+pformat(report_info))

		returnVal = { "report_name" : reportName,"report_ref" : str(report_info[6]) + '/' + str(report_info[0]) + '/' + str(report_info[4]) }
        except Exception, e:
                raise KBaseRNASeqException("Create Reference Annotation Failed: {0}".format(e))
        finally:
                handler_util.cleanup(self.__LOGGER,gtf_dir)
		#if os.path.exists(out_file_path): os.remove(out_file_path)
	
        #END GetFeaturesToGTF

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method GetFeaturesToGTF return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

    def Bowtie2Call(self, ctx, params):
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN Bowtie2Call
	user_token=ctx['token']
	#pprint(params)
        ws_client=Workspace(url=self.__WS_URL, token=user_token)
        hs = HandleService(url=self.__HS_URL, token=user_token)
        try:
	    #if os.path.exists(self.__SCRATCH):
            #       shutil.rmtree(self.__SCRATCH)
            #os.makedirs(self.__SCRATCH)
            if not os.path.exists(self.__SCRATCH): os.makedirs(self.__SCRATCH)
            bowtie2_dir = self.__SCRATCH+'/tmp'
            if os.path.exists(bowtie2_dir):
                handler_util.cleanup(self.__LOGGER,bowtie2_dir)
            if not os.path.exists(bowtie2_dir): os.makedirs(bowtie2_dir)

            self.__LOGGER.info("Downloading RNASeq Sample file")
	    try:
                sample ,reference,bowtie_index = ws_client.get_objects(
                                        [{'name' : params['sample_id'],'workspace' : params['ws_id']},
                                        { 'name' : params['reference'], 'workspace' : params['ws_id']},
                                        { 'name' : params['bowtie2_index'], 'workspace' : params['ws_id']}])
            except Exception,e:
                 self.__LOGGER.exception("".join(traceback.format_exc()))
                 raise KBaseRNASeqException("Error Downloading objects from the workspace ")
	    opts_dict = { k:v for k,v in params.iteritems() if not k in ('ws_id','sample_id','reference','bowtie_index','analysis_id','output_obj_name') and v is not None }

	    if 'data' in sample and sample['data'] is not None:
                #self.__LOGGER.info("getting here")
                if 'metadata' in sample['data'] and sample['data']['metadata'] is not None:
                        genome = sample['data']['metadata']['genome_id']
                        #self.__LOGGER.info(genome)
            if 'singleend_sample' in sample['data'] and sample['data']['singleend_sample'] is not None:
                lib_type = "SingleEnd"
                singleend_sample = sample['data']['singleend_sample']
                sample_shock_id = singleend_sample['handle']['id']
                sample_filename = singleend_sample['handle']['file_name']
                try:
                     script_util.download_file_from_shock(self.__LOGGER, shock_service_url=self.__SHOCK_URL, shock_id=sample_shock_id,filename=singleend_sample['handle']['file_name'], directory=bowtie2_dir,token=user_token)
                except Exception,e:
                        raise Exception( "Unable to download shock file , {0}".format(e))
            if 'pairedend_sample' in sample['data'] and sample['data']['pairedend_sample'] is not None:
                lib_type = "PairedEnd"
                pairedend_sample = sample['data']['pairedend_sample']
                if "handle_1" in pairedend_sample and "id" in pairedend_sample['handle_1']:
                        sample_shock_id1  = pairedend_sample['handle_1']['id']
                if "handle_1" in pairedend_sample and "file_name" in pairedend_sample['handle_1']:
                        filename1 = pairedend_sample['handle_1']['file_name']
                if sample_shock_id1 is None:
                        raise Exception("Handle1 there was not shock id found.")
                if "handle_2" in pairedend_sample  and "id" in pairedend_sample['handle_2']:
                        sample_shock_id2  = pairedend_sample['handle_2']['id']
                if "handle_2" in pairedend_sample and "file_name" in pairedend_sample['handle_2']:
                        filename2 = pairedend_sample['handle_2']['file_name']

                if sample_shock_id2 is None:
                        raise Exception("Handle2 there was not shock id found.")
                try:
                        script_util.download_file_from_shock(self.__LOGGER, shock_service_url=self.__SHOCK_URL, shock_id=sample_shock_id1,filename=filename1,directory=bowtie2_dir, token=user_token)
                        script_util.download_file_from_shock(self.__LOGGER,shock_service_url=self.__SHOCK_URL, shock_id=sample_shock_id2,filename=filename2,directory=bowtie2_dir, token=user_token)
                except Exception,e:
                        raise Exception( "Unable to download shock file , {0}".format(e))

            if 'analysis_id' in sample['data'] and sample['data']['analysis_id'] is not None:
		# updata the analysis object with the alignment id
                analysis_id = sample['data']['analysis_id']
                #self.__LOGGER.info("RNASeq Sample belongs to the {0}".format(analysis_id))
	    if 'handle' in bowtie_index['data'] and bowtie_index['data']['handle'] is not None:
                b_shock_id = bowtie_index['data']['handle']['id']
                b_filename = bowtie_index['data']['handle']['file_name']
                b_filesize = bowtie_index['data']['size']
            try:
                self.__LOGGER.info("Downloading Bowtie2 Indices from Shock")
                script_util.download_file_from_shock(self.__LOGGER, shock_service_url=self.__SHOCK_URL, shock_id=b_shock_id,filename=b_filename,directory=bowtie2_dir,filesize=b_filesize,token=user_token)
            except Exception,e :
                self.__LOGGER.exception("".join(traceback.format_exc()))
                raise Exception( "Unable to download shock file , {0}".format(e))
	    try:
                self.__LOGGER.info("Unzipping Bowtie2 Indices")
                script_util.unzip_files(self.__LOGGER,os.path.join(bowtie2_dir,b_filename),bowtie2_dir)
		mv_dir= handler_util.get_dir(bowtie2_dir)
                if mv_dir is not None:
                        script_util.move_files(self.__LOGGER,mv_dir,bowtie2_dir)
		#script_util.move_files(self.__LOGGER,handler_util.get_dir(bowtie2_dir),bowtie2_dir)
            except Exception, e:
                   self.__LOGGER.error("".join(traceback.format_exc()))
                   raise Exception("Unzip indexfile error: Please contact help@kbase.us")
            # Define the bowtie2 options
	    os.makedirs(os.path.join(bowtie2_dir,params['output_obj_name']))
	    output_dir = os.path.join(bowtie2_dir,params['output_obj_name'])
	    out_file = output_dir +"/accepted_hits.sam"
	    bowtie2_base =os.path.join(bowtie2_dir,handler_util.get_file_with_suffix(bowtie2_dir,".rev.1.bt2"))

            ### Adding advanced options to Bowtie2Call
	    bowtie2_cmd = '' 
	    if('quality_score' in params and params['quality_score'] is not None): bowtie2_cmd += ( ' --'+params['quality_score'])
	    if('alignment_type' in params and params['alignment_type'] is not None): bowtie2_cmd += ( ' --'+params['alignment_type'] )
	    if('preset_options' in params and params['preset_options'] is not None ) and ('alignment_type' in params and params['alignment_type'] is not None):
		 if (params['alignment_type'] == 'local'):
			 bowtie2_cmd += (' --'+params['preset_options']+'-local')
	    	 else: bowtie2_cmd += (' --'+params['preset_options'] )
	    if(lib_type == "SingleEnd"):
                sample_file = os.path.join(bowtie2_dir,sample_filename)
                bowtie2_cmd += " -U {0} -x {1} -S {2}".format(sample_file,bowtie2_base,out_file)
            elif(lib_type == "PairedEnd"):
                sample_file1 = os.path.join(bowtie2_dir,filename1)
                sample_file2 = os.path.join(bowtie2_dir,filename2)
                bowtie2_cmd += " -1 {0} -2 {1} -x {2} -S {3}".format(sample_file1,sample_file2,bowtie2_base,out_file)	
	    
            try:
	        self.__LOGGER.info("Executing: bowtie2 {0}".format(bowtie2_cmd))	
                cmdline_output = script_util.runProgram(self.__LOGGER,"bowtie2",bowtie2_cmd,None,bowtie2_dir)
                #cmdline_output = script_util.runProgram(self.__LOGGER,"bowtie2",bowtie2_cmd,None,os.getcwd())
		bam_file = os.path.join(output_dir,"accepted_hits_unsorted.bam")
		sam_to_bam = "view -bS -o {0} {1}".format(bam_file,out_file)
		script_util.runProgram(self.__LOGGER,"samtools",sam_to_bam,None,bowtie2_dir)
		#script_util.runProgram(self.__LOGGER,"samtools",sam_to_bam,None,os.getcwd())
		final_bam_prefix = os.path.join(output_dir,"accepted_hits")
		sort_bam_cmd  = "sort {0} {1}".format(bam_file,final_bam_prefix)
		script_util.runProgram(self.__LOGGER,"samtools",sort_bam_cmd,None,bowtie2_dir)
		#script_util.runProgram(self.__LOGGER,"samtools",sort_bam_cmd,None,os.getcwd())
                #script_util.runProgram(self.__LOGGER,self.__SCRIPT_TYPE['tophat_script'],tophat_cmd,self.__SCRIPTS_DIR,os.getcwd())
            except Exception,e:
                raise KBaseRNASeqException("Error Running the bowtie2 command {0},{1},{2}".format(bowtie2_cmd,bowtie2_dir,e))
            try:
                bam_file = output_dir+"/accepted_hits.bam"
                align_stats_cmd="flagstat {0}".format(bam_file)
                stats = script_util.runProgram(self.__LOGGER,"samtools",align_stats_cmd,None,bowtie2_dir)
                # Pass it to the stats['result']
                stats_obj_name = params['output_obj_name']+"_"+str(hex(uuid.getnode()))+"_AlignmentStats"
                script_util.extractStatsInfo(self.__LOGGER,ws_client,params['ws_id'],params['output_obj_name'],stats['result'],stats_obj_name)
            except Exception , e :
                self.__LOGGER.exception("Failed to create RNASeqAlignmentStats: {0}".format(e))
                raise KBaseRNASeqException("Failed to create RNASeqAlignmentStats: {0}".format(e))

        # Zip tophat folder
            try:
                out_file_path = os.path.join(self.__SCRATCH,"%s.zip" % params['output_obj_name'])
		script_util.zip_files(self.__LOGGER, output_dir,out_file_path)
                #out_file_path = os.path.join(self.__SCRATCH,"%s.zip" % params['output_obj_name'])
                #handler_util.cleanup(self.__LOGGER,tophat_dir)
            except Exception, e:
                raise KBaseRNASeqException("Failed to compress the index: {0}".format(e))
            ## Upload the file using handle service
            try:
		
                #bowtie2_handle = script_util.create_shock_handle(self.__LOGGER,"%s.zip" % params['output_obj_name'],self.__SHOCK_URL,self.__HS_URL,"Zip",user_token)
		bowtie2_handle = hs.upload(out_file_path)
		#if self.__PUBLIC_SHOCK_NODE is 'true':
                #      script_util.shock_node_2b_public(self.__LOGGER,node_id=bowtie2_handle['id'],shock_service_url=bowtie2_handle['url'],token=user_token)
            except Exception, e:
                raise KBaseRNASeqException("Failed to upload the index: {0}".format(e))
            bowtie2_out = { "file" : bowtie2_handle ,"size" : os.path.getsize(out_file_path), "aligned_using" : "bowtie2" , "aligner_version" : "2.2.6","metadata" :  sample['data']['metadata']}
            returnVal = bowtie2_out

            ## Save object to workspace
            self.__LOGGER.info( "Saving bowtie2 object to  workspace")
            try:
                res= ws_client.save_objects(
                                        {"workspace":params['ws_id'],
                                         "objects": [{
                                         "type":"KBaseRNASeq.RNASeqSampleAlignment",
                                         "data":bowtie2_out,
                                         "name":params['output_obj_name']}
                                        ]})
		map_key = script_util.get_obj_info(self.__LOGGER,self.__WS_URL,[params['sample_id']],params["ws_id"],user_token)[0]
                map_value = script_util.get_obj_info(self.__LOGGER,self.__WS_URL,[params['output_obj_name']],params["ws_id"],user_token)[0]
                self.__LOGGER.info( "Updating the Analysis object")
                if 'analysis_id' in sample['data']  and sample['data']['analysis_id'] is not None:
                    analysis_obj = "/".join(sample['data']['analysis_id'].split('/')[0:2])
                    script_util.updateAnalysisTO(self.__LOGGER, ws_client, 'alignments', map_key, map_value,analysis_obj,  params['ws_id'], int(analysis_obj.split('/')[1]))


            except Exception, e:
                raise KBaseRNASeqException("Failed to upload  the alignment: {0}".format(e))
	    returnVal = { "stats_obj" : stats_obj_name , "alignment_id" : params['output_obj_name'] , "analysis_id" : analysis_obj }
	except Exception,e:
                 self.__LOGGER.exception("".join(traceback.format_exc()))
                 raise KBaseRNASeqException("Error Running Bowtie2Call")
	finally:
                 handler_util.cleanup(self.__LOGGER,bowtie2_dir)
		 #if os.path.exists(out_file_path): os.remove(out_file_path)
        #END Bowtie2Call

        # At some point might do deeper type checking...
        if not isinstance(returnVal, object):
            raise ValueError('Method Bowtie2Call return value ' +
                             'returnVal is not type object as required.')
        # return the results
        return [returnVal]

    def TophatCall(self, ctx, params):
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN TophatCall
       

        ## TODO: Need to take Analysis TO as input object instead of sample id

	user_token=ctx['token']
	#pprint(params)
        ws_client=Workspace(url=self.__WS_URL, token=user_token)
	ws_client=Workspace(url=self.__WS_URL, token=user_token)
        hs = HandleService(url=self.__HS_URL, token=user_token)
	try:
	    ### Make a function to download the workspace object  and prepare dict of genome ,lib_type 
	    #if os.path.exists(self.__SCRATCH):
            # 	handler_util.cleanup(self.__LOGGER,self.__SCRATCH)
	    if not os.path.exists(self.__SCRATCH): os.makedirs(self.__SCRATCH)
	    tophat_dir = self.__SCRATCH +'/tmp'
	    print tophat_dir
            if os.path.exists(tophat_dir):
	    	handler_util.cleanup(self.__LOGGER,tophat_dir)
            if not os.path.exists(tophat_dir): os.makedirs(tophat_dir)

	    self.__LOGGER.info("Downloading RNASeq Sample file")
	    try:
            	sample ,reference,bowtie_index,annotation = ws_client.get_objects(
                                        [{'name' : params['sample_id'],'workspace' : params['ws_id']},
					{ 'name' : params['reference'], 'workspace' : params['ws_id']},
					{ 'name' : params['bowtie_index'], 'workspace' : params['ws_id']},
					{ 'name' : params['annotation_gtf'] , 'workspace' : params['ws_id']}])
            except Exception,e:
		 self.__LOGGER.exception("".join(traceback.format_exc()))
		 raise KBaseRNASeqException("Error Downloading objects from the workspace ") 
                     
	    opts_dict = { k:v for k,v in params.iteritems() if not k in ('ws_id','sample_id','reference','bowtie_index','annotation_gtf','analysis_id','output_obj_name') and v is not None }
	    
 
            if 'data' in sample and sample['data'] is not None:
		#self.__LOGGER.info("getting here")
		if 'metadata' in sample['data'] and sample['data']['metadata'] is not None:
			genome = sample['data']['metadata']['genome_id']
			#self.__LOGGER.info(genome)
	    if 'singleend_sample' in sample['data'] and sample['data']['singleend_sample'] is not None:
		lib_type = "SingleEnd"
		singleend_sample = sample['data']['singleend_sample']
		sample_shock_id = singleend_sample['handle']['id']
		sample_filename = singleend_sample['handle']['file_name']
		try:
               	     script_util.download_file_from_shock(self.__LOGGER, shock_service_url=self.__SHOCK_URL, shock_id=sample_shock_id,filename=singleend_sample['handle']['file_name'], directory=tophat_dir,token=user_token)
        	except Exception,e:
                	raise Exception( "Unable to download shock file , {0}".format(e))
	    if 'pairedend_sample' in sample['data'] and sample['data']['pairedend_sample'] is not None: 
		lib_type = "PairedEnd"
		pairedend_sample = sample['data']['pairedend_sample']
		#self.__LOGGER.info(lib_type)
		if "handle_1" in pairedend_sample and "id" in pairedend_sample['handle_1']:
                	sample_shock_id1  = pairedend_sample['handle_1']['id']
        	if "handle_1" in pairedend_sample and "file_name" in pairedend_sample['handle_1']:
                	filename1 = pairedend_sample['handle_1']['file_name']
        	if sample_shock_id1 is None:
                	raise Exception("Handle1 there was not shock id found.")
        	if "handle_2" in pairedend_sample  and "id" in pairedend_sample['handle_2']:
                	sample_shock_id2  = pairedend_sample['handle_2']['id']
        	if "handle_2" in pairedend_sample and "file_name" in pairedend_sample['handle_2']:
                	filename2 = pairedend_sample['handle_2']['file_name']

        	if sample_shock_id2 is None:
                	raise Exception("Handle2 there was not shock id found.")
		try:
        		script_util.download_file_from_shock(self.__LOGGER, shock_service_url=self.__SHOCK_URL, shock_id=sample_shock_id1,filename=filename1,directory=tophat_dir, token=user_token)
        		script_util.download_file_from_shock(self.__LOGGER,shock_service_url=self.__SHOCK_URL, shock_id=sample_shock_id2,filename=filename2,directory=tophat_dir, token=user_token)
                except Exception,e:
                        raise Exception( "Unable to download shock file , {0}".format(e))

	    # Download bowtie_Indexes
	    if 'handle' in bowtie_index['data'] and bowtie_index['data']['handle'] is not None:
		b_shock_id = bowtie_index['data']['handle']['id']
		b_filename = bowtie_index['data']['handle']['file_name']
		b_filesize = bowtie_index['data']['size']
	    try:
                self.__LOGGER.info("Downloading Bowtie2 Indices from Shock")
		script_util.download_file_from_shock(self.__LOGGER, shock_service_url=self.__SHOCK_URL, shock_id=b_shock_id,filename=b_filename,directory=tophat_dir,filesize=b_filesize,token=user_token)
	    except Exception,e :
		self.__LOGGER.exception("".join(traceback.format_exc()))
		raise Exception( "Unable to download shock file , {0}".format(e))

	    try:
                self.__LOGGER.info("Unzipping Bowtie2 Indices")
		index_path = os.path.join(tophat_dir,b_filename)
                script_util.unzip_files(self.__LOGGER,index_path,tophat_dir)
		mv_dir= handler_util.get_dir(tophat_dir)
		if mv_dir is not None:
			script_util.move_files(self.__LOGGER,mv_dir,tophat_dir)
            except Exception, e:
                   self.__LOGGER.exception("".join(traceback.format_exc()))
                   raise Exception("Unzip indexfile error: Please contact help@kbase.us")
	    
            if 'handle' in annotation['data'] and annotation['data']['handle'] is not None:
                a_shock_id = annotation['data']['handle']['id']
                a_filename = annotation['data']['handle']['file_name']
		a_filesize = annotation['data']['size']
            try:
                self.__LOGGER.info("Downloading Reference Annotation from Shock")
                script_util.download_file_from_shock(self.__LOGGER, shock_service_url=self.__SHOCK_URL, shock_id=a_shock_id,filename=a_filename,directory=tophat_dir,filesize=a_filesize,token=user_token)
            except Exception,e :
		self.__LOGGER.exception("".join(traceback.format_exc()))
                raise Exception( "Unable to download shock file , {0}".format(e))
	    output_dir = os.path.join(tophat_dir,params['output_obj_name'])
	    gtf_file = os.path.join(tophat_dir,a_filename)
	    bowtie_base =os.path.join(tophat_dir,handler_util.get_file_with_suffix(tophat_dir,".rev.1.bt2"))
	    num_p = multiprocessing.cpu_count()
	    #print 'processors count is ' +  str(num_p)
	    tophat_cmd = (' -p '+str(num_p))
	    #if('num_threads' in opts_dict ) :  tophat_cmd += (' -p '+str(num_p))
	    #if('num_threads' in opts_dict ) :  tophat_cmd += (' -p '+str(opts_dict['num_threads']))
	    if('max_intron_length' in opts_dict ) : tophat_cmd += (' -I '+str(opts_dict['max_intron_length']))
	    if('min_intron_length' in opts_dict ) : tophat_cmd += (' -i '+str(opts_dict['min_intron_length']))
	    if('read_edit_dist' in opts_dict ) : tophat_cmd += (' --read-edit-dist '+str(opts_dict['read_edit_dist']))
	    if('read_gap_length' in opts_dict ) : tophat_cmd += (' --read-gap-length '+str(opts_dict['read_gap_length']))
	    if('read_mismatches' in opts_dict) : tophat_cmd += (' -N '+str(opts_dict['read_mismatches']))
	    if('library_type' in opts_dict) : tophat_cmd += (' --library-type ' + opts_dict['library_type'])
	    if('report_secondary_alignments' in opts_dict and int(opts_dict['report_secondary_alignments']) == 1) : tophat_cmd += ' --report-secondary-alignments'
	    if('no_coverage_search' in opts_dict and int(opts_dict['no_coverage_search']) == 1): tophat_cmd += ' --no-coverage-search'
	    if(lib_type == "SingleEnd"):
                sample_file = os.path.join(tophat_dir,sample_filename)
                tophat_cmd += ' -o {0} -G {1} {2} {3}'.format(output_dir,gtf_file,bowtie_base,sample_file)
            elif(lib_type == "PairedEnd"):
                sample_file1 = os.path.join(tophat_dir,filename1)
                sample_file2 = os.path.join(tophat_dir,filename2)
                tophat_cmd += ' -o {0} -G {1} {2} {3} {4}'.format(output_dir,gtf_file,bowtie_base,sample_file1,sample_file2)
	    self.__LOGGER.info("Executing: tophat {0}".format(tophat_cmd)) 
	    try:  
            	script_util.runProgram(self.__LOGGER,"tophat",tophat_cmd,None,tophat_dir)
            	#script_util.runProgram(self.__LOGGER,"tophat",tophat_cmd,None,os.getcwd())
            	#script_util.runProgram(self.__LOGGER,self.__SCRIPT_TYPE['tophat_script'],tophat_cmd,self.__SCRIPTS_DIR,os.getcwd())
            except Exception,e:
                raise KBaseRNASeqException("Error Running the tophat command and the samtools flagstat {0},{1},{2}".format(tophat_cmd,tophat_dir,e))

            self.__LOGGER.info("Generating Alignment Statistics")
	    try:
                bam_file = output_dir+"/accepted_hits.bam"
                align_stats_cmd="flagstat {0}".format(bam_file)
                stats = script_util.runProgram(self.__LOGGER,"samtools",align_stats_cmd,None,tophat_dir)
                # Pass it to the stats['result']
		stats_obj_name = params['output_obj_name']+"_"+str(hex(uuid.getnode()))+"_AlignmentStats"
                script_util.extractStatsInfo(self.__LOGGER,ws_client,params['ws_id'],params['output_obj_name'],stats['result'],stats_obj_name)
            except Exception , e :
                self.__LOGGER.exception("Failed to create RNASeqAlignmentStats: {0}".format(e))
                raise KBaseRNASeqException("Failed to create RNASeqAlignmentStats: {0}".format(e))


	# Zip tophat folder
            try:
                out_file_path = os.path.join(self.__SCRATCH,"%s.zip" % params['output_obj_name'])
                script_util.zip_files(self.__LOGGER, output_dir,out_file_path)
                #out_file_path = os.path.join("%s.zip" % params['output_obj_name'])
		#handler_util.cleanup(self.__LOGGER,tophat_dir)
            except Exception, e:
                raise KBaseRNASeqException("Failed to compress the index: {0}".format(e))
            ## Upload the file using handle service
            try:
		 tophat_handle = hs.upload(out_file_path)
                 #tophat_handle = script_util.create_shock_handle(self.__LOGGER,"%s.zip" % params['output_obj_name'],self.__SHOCK_URL,self.__HS_URL,"Zip",user_token)
		 #if self.__PUBLIC_SHOCK_NODE is 'true':
                 #       script_util.shock_node_2b_public(self.__LOGGER,node_id=tophat_handle['id'],shock_service_url=tophat_handle['url'],token=user_token)	
            except Exception, e:
                raise KBaseRNASeqException("Failed to upload the index: {0}".format(e))
            tophat_out = { "file" : tophat_handle ,"size" : os.path.getsize(out_file_path), "aligned_using" : "tophat" , "aligner_version" : "3.1.0","metadata" :  sample['data']['metadata']}
	     
	    ## Save object to workspace
            self.__LOGGER.info( "Saving Tophat object to  workspace")
	    try:
            	res= ws_client.save_objects(
                                        {"workspace":params['ws_id'],
                                         "objects": [{
                                         "type":"KBaseRNASeq.RNASeqSampleAlignment",
                                         "data":tophat_out,
                                         "name":params['output_obj_name']}
                                        ]})
	        self.__LOGGER.info( "Updating the Analysis object")
		map_key = script_util.get_obj_info(self.__LOGGER,self.__WS_URL,[params['sample_id']],params["ws_id"],user_token)[0]
                map_value = script_util.get_obj_info(self.__LOGGER,self.__WS_URL,[params['output_obj_name']],params["ws_id"],user_token)[0]	
                if 'analysis_id' in sample['data']  and sample['data']['analysis_id'] is not None:
		    analysis_obj = "/".join(sample['data']['analysis_id'].split('/')[0:2])
		    script_util.updateAnalysisTO(self.__LOGGER, ws_client, 'alignments', map_key, map_value,analysis_obj,  params['ws_id'], int(analysis_obj.split('/')[1]))
            except Exception, e:
                    self.__LOGGER.exception("Failed to upload the alignment: {0}".format(e))
                    raise KBaseRNASeqException("Failed to upload  the alignment: {0}".format(e))
	    returnVal = { "stats_obj" : stats_obj_name , "alignment_id" : params['output_obj_name'] , "analysis_id" : analysis_obj }	
	except Exception,e:
            raise KBaseRNASeqException("Error Running Tophatcall {0}".format("".join(traceback.format_exc())))
	finally:
	    handler_util.cleanup(self.__LOGGER,tophat_dir)
	    #if os.path.exists(out_file_path): os.remove(out_file_path)
	     
        #END TophatCall

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method TophatCall return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

    def CufflinksCall(self, ctx, params):
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN CufflinksCall
	user_token=ctx['token']
	#pprint(params)
        self.__LOGGER.info("Started CufflinksCall")
        
        ws_client=Workspace(url=self.__WS_URL, token=user_token)
        hs = HandleService(url=self.__HS_URL, token=user_token)
        try:
            #if os.path.exists(self.__SCRATCH):
            #    handler_util.cleanup(self.__LOGGER,self.__SCRATCH)
            if not os.path.exists(self.__SCRATCH): os.makedirs(self.__SCRATCH) 
	    cufflinks_dir = self.__SCRATCH +'/tmp'
            if os.path.exists(cufflinks_dir):
                handler_util.cleanup(self.__LOGGER,cufflinks_dir)
            if not os.path.exists(cufflinks_dir): os.makedirs(cufflinks_dir)

            self.__LOGGER.info("Downloading Alignment Sample file")
	    try:
                sample,annotation_gtf = ws_client.get_objects(
                                        [{'name' : params['alignment_sample_id'],'workspace' : params['ws_id']},
                                         {'name' : params['annotation_gtf'], 'workspace' : params['ws_id']}])
            except Exception,e:
                 self.__LOGGER.exception("".join(traceback.format_exc()))
                 raise KBaseRNASeqException("Error Downloading objects from the workspace ")
	    opts_dict = { k:v for k,v in params.iteritems() if not k in ('ws_id','alignment_sample_id','annotation_gtf','num_threads','min-intron-length','max-intron-length','overhang-tolerance','output_obj_name') and v is not None }

            ## Downloading data from shock
	    if 'data' in sample and sample['data'] is not None:
                self.__LOGGER.info("Downloading Sample Alignment")
                try:
                     script_util.download_file_from_shock(self.__LOGGER, shock_service_url=self.__SHOCK_URL, shock_id=sample['data']['file']['id'],filename=sample['data']['file']['file_name'], directory=cufflinks_dir,token=user_token)
                except Exception,e:
                        raise Exception( "Unable to download shock file, {0}".format(e))
	        try:
                    script_util.unzip_files(self.__LOGGER,os.path.join(cufflinks_dir,sample['data']['file']['file_name']),cufflinks_dir)
		    #script_util.move_files(self.__LOGGER,handler_util.get_dir(cufflinks_dir),cufflinks_dir)
                except Exception, e:
		       self.__LOGGER.error("".join(traceback.format_exc()))
                       raise Exception("Unzip indexfile error: Please contact help@kbase.us")
            else:
                raise KBaseRNASeqException("No data was included in the referenced sample id");
	    if 'data' in annotation_gtf and annotation_gtf['data'] is not None:
                self.__LOGGER.info("Downloading Reference Annotation")
                try:
                     agtf_fn = annotation_gtf['data']['handle']['file_name']
                     script_util.download_file_from_shock(self.__LOGGER, shock_service_url=self.__SHOCK_URL, shock_id=annotation_gtf['data']['handle']['id'],filename=agtf_fn, directory=cufflinks_dir,token=user_token)
                except Exception,e:
                        raise Exception( "Unable to download shock file, {0}".format(e))
            else:
                raise KBaseRNASeqException("No data was included in the referenced ReferenceAnnotation");

            ##  now ready to call
	    output_dir = os.path.join(cufflinks_dir, params['output_obj_name'])
	    input_file = os.path.join(cufflinks_dir,"accepted_hits.bam")
	    gtf_file = os.path.join(cufflinks_dir,agtf_fn)
            try:
		num_p = multiprocessing.cpu_count()
                #print 'processors count is ' +  str(num_p)
		cufflinks_command = (' -p '+str(num_p))
                #if 'num_threads' in params and params['num_threads'] is not None:
                #     cufflinks_command += (' -p '+str(params['num_threads']))
		if 'max-intron-length' in params and params['max-intron-length'] is not None:
		     cufflinks_command += (' --max-intron-length '+str(params['max-intron-length']))
		if 'min-intron-length' in params and params['min-intron-length'] is not None:
		     cufflinks_command += (' --min-intron-length '+str(params['min-intron-length']))
		if 'overhang-tolerance' in params  and params['overhang-tolerance'] is not None:
		     cufflinks_command += (' --overhang-tolerance '+str(params['overhang-tolerance']))
		
		cufflinks_command += " -o {0} -G {1} {2}".format(output_dir,gtf_file,input_file)
                self.__LOGGER.info("Executing: cufflinks {0}".format(cufflinks_command))
		script_util.runProgram(self.__LOGGER,"cufflinks",cufflinks_command,None,cufflinks_dir)

            except Exception,e:
                raise KBaseRNASeqException("Error executing cufflinks {0},{1},{2}".format(cufflinks_command,cufflinks_dir,e))
            ##Parse output files
	    exp_dict = script_util.parse_FPKMtracking(os.path.join(output_dir,"genes.fpkm_tracking"))
            ##  compress and upload to shock
            try:
                self.__LOGGER.info("Zipping Cufflinks output")
		out_file_path = os.path.join(self.__SCRATCH,"%s.zip" % params['output_obj_name'])
                script_util.zip_files(self.__LOGGER,output_dir,out_file_path)
                #handle = hs.upload("{0}.zip".format(params['output_obj_name']))
            except Exception,e:
		self.__LOGGER.exception("".join(traceback.format_exc()))
                raise KBaseRNASeqException("Error executing cufflinks {0},{1}".format(os.getcwd(),e))
	    try:
		#out_file_path = os.path.join(self.__SCRATCH,"%s.zip" % params['output_obj_name'])
		handle = hs.upload(out_file_path)
            except Exception, e:
	        self.__LOGGER.exception("".join(traceback.format_exc()))	
                raise KBaseRNASeqException("Error while zipping the output objects: {0}".format(e))

	    ## Save object to workspace
	    try:
                self.__LOGGER.info("Saving Cufflinks object to workspace")
                es_obj = { 'id' : '1234',
                           'source_id' : 'source_id',
                           'type' : 'RNA-Seq',
                           'numerical_interpretation' : 'FPKM',
                           'external_source_date' : 'external_source_date',
                           'expression_levels' : exp_dict,
			   'genome_id' : sample['data']['metadata']['genome_id'],
                           'data_source' : 'data_source',
                           'shock_url' : "{0}/node/{1}".format(handle['url'],handle['id'])
                }

            	res= ws_client.save_objects(
                                        {"workspace":params['ws_id'],
                                         "objects": [{
                                         "type":"KBaseExpression.ExpressionSample",
                                         "data":es_obj,
                                         "name":params['output_obj_name']}
                                        ]})
                self.__LOGGER.info( "Updating the Analysis object")
                map_key = script_util.get_obj_info(self.__LOGGER,self.__WS_URL,[sample['data']['metadata']['sample_id']],params["ws_id"],user_token) # it will be the same one
                map_value = script_util.get_obj_info(self.__LOGGER,self.__WS_URL,[params['output_obj_name']],params["ws_id"],user_token)
		rna_sample = ws_client.get_objects([{'ref' : map_key[0] }])[0]
		
                if 'analysis_id' in rna_sample['data']  and rna_sample['data']['analysis_id'] is not None:
		    analysis_obj = "/".join(rna_sample['data']['analysis_id'].split('/')[0:2])
		    script_util.updateAnalysisTO(self.__LOGGER, ws_client, 'expression_values', map_key[0], map_value[0], analysis_obj,  params['ws_id'], int(analysis_obj.split('/')[1]))
                    
	    except Exception, e:
		self.__LOGGER.exception("".join(traceback.format_exc()))
                raise KBaseRNASeqException("Failed to upload the ExpressionSample: {0}".format(e))
	    returnVal = params['output_obj_name']
	except KBaseRNASeqException,e:
                 self.__LOGGER.exception("".join(traceback.format_exc()))
                 raise KBaseRNASeqException("Error Running Cufflinks : {0}".format(e))
        finally:
                 handler_util.cleanup(self.__LOGGER,cufflinks_dir)
		 #if os.path.exists(out_file_path): os.remove(out_file_path)	
        #END CufflinksCall

        # At some point might do deeper type checking...
        if not isinstance(returnVal, basestring):
            raise ValueError('Method CufflinksCall return value ' +
                             'returnVal is not type basestring as required.')
        # return the results
        return [returnVal]

    def CuffmergeCall(self, ctx, params):
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN CuffmergeCall
	user_token=ctx['token']
	#pprint(params)
        self.__LOGGER.info("Started CuffmergeCall")
        
        ws_client=Workspace(url=self.__WS_URL, token=user_token)
        hs = HandleService(url=self.__HS_URL, token=user_token)
        try:
	    #if os.path.exists(self.__SCRATCH):
            #    handler_util.cleanup(self.__LOGGER,self.__SCRATCH)
            if not os.path.exists(self.__SCRATCH): os.makedirs(self.__SCRATCH)
            cuffmerge_dir = self.__SCRATCH +'/tmp'
            if os.path.exists(cuffmerge_dir):
                handler_util.cleanup(self.__LOGGER,cuffmerge_dir)
            if not os.path.exists(cuffmerge_dir): os.makedirs(cuffmerge_dir)
	    provenance = [{}]
            if 'provenance' in ctx:
                provenance = ctx['provenance']
                # add additional info to provenance here, in this case the input data object reference
            provenance[0]['input_ws_objects']=[params['ws_id']+'/'+params['analysis']] 
            self.__LOGGER.info("Downloading Analysis file")
	    try:
                analysis = ws_client.get_objects(
                                        [{'name' : params['analysis'],'workspace' : params['ws_id']}])[0]
            except Exception,e:
                 self.__LOGGER.exception("".join(traceback.format_exc()))
                 raise KBaseRNASeqException("Error Downloading objects from the workspace ")
	    
            ## Downloading data from shock
            list_file = open(cuffmerge_dir+"/"+self.__ASSEMBLY_GTF_FN,'w')
	    if 'data' in analysis : #and analysis['data'] is not None:
		if 'annotation_id' in analysis['data']:
			annotation=ws_client.get_objects([{'ref' : analysis['data']['annotation_id']} ])[0]
			annotation_name = annotation['data']['handle']['file_name']
			try:
                         script_util.download_file_from_shock(self.__LOGGER, shock_service_url=annotation['data']['handle']['url'], shock_id=annotation['data']['handle']['id'],filename=annotation_name, directory=cuffmerge_dir,token=user_token)
                    	except Exception,e:
                            raise Exception( "Unable to download shock file, {0}".format(e))
                self.__LOGGER.info("Downloading each expression")
			
                shock_re =  re.compile(r'^(.*)/node/([^?]*)\??')
                # TODO: Change expression_values object design
		le = analysis['data']['expression_values']
                #for le in analysis['data']['expression_values']:
                for k,v in le.items():
                    ko,vo=ws_client.get_objects([{'ref' : k}, {'ref' : v} ])
                    sp = os.path.join(cuffmerge_dir, ko['info'][1]) 
		    if not os.path.exists(sp): os.makedirs(sp)
                   
                    if 'shock_url' not in vo['data']:
                        self.__LOGGER.info("{0} does not contain shock_url and we skip {1}".format(vo['info'][1], v))
                        next 

                    se = shock_re.search(vo['data']['shock_url'])
                    if se is None: 
                        self.__LOGGER.info("{0} does not contain shock_url and we skip {1}".format(vo['info'][1], v))
                        next 

                    efn = "{0}.zip".format(vo['info'][1])
                    try:
                         script_util.download_file_from_shock(self.__LOGGER, shock_service_url=se.group(1), shock_id=se.group(2),filename=efn, directory=cuffmerge_dir,token=user_token)
                    except Exception,e:
                            raise Exception( "Unable to download shock file, {0}".format(e))
	            try:
                        script_util.unzip_files(self.__LOGGER,os.path.join(cuffmerge_dir,efn),sp)
                    except Exception, e:
                           raise Exception("Unzip cufflinks file  error: Please contact help@kbase.us")
                    if not os.path.exists("{0}/transcripts.gtf\n".format(sp)):
                       # Would it be better to be skipping this? if so, replace Exception to be next
		       next		   
                       #raise Exception("{0} does not contain transcripts.gtf:  {1}".format(vo['info'][1], v))
                    list_file.write("{0}/transcripts.gtf\n".format(sp))
            else:
                raise KBaseRNASeqException("No data was included in the referenced analysis");
            list_file.close()

            ##  now ready to call
	    output_dir = os.path.join(cuffmerge_dir, params['output_obj_name'])
            try:
                # TODO: add reference GTF later, seems googledoc command looks wrong
		num_p = multiprocessing.cpu_count()
	        #print 'processors count is ' +  str(num_p)
            	#cuffmerge_command = (' -p '+str(num_p))
		cuffmerge_command = " -p {0} -o {1} -g {2}/{3} {4}/{5}".format(str(num_p),output_dir,cuffmerge_dir,annotation_name,cuffmerge_dir,self.__ASSEMBLY_GTF_FN)
                #command_list= ['cuffmerge', '-o', output_dir, '-G', agtf_fn, "{0}/accepted_hits.bam".format(cuffmerge_dir)]
                #if 'num_threads' in params and params['num_threads'] is not None:
                #     command_list.append('-p')
                #     command_list.append(params['num_threads'])
                #for arg in ['min-intron-length','max-intron-length','overhang-tolerance']:
                #    if arg in params and params[arg] is not None:
                #         command_list.append('--{0}'.format(arg))
                #         command_list.append(params[arg])

                self.__LOGGER.info("Executing: cuffmerge {0}".format(cuffmerge_command))
	        cmdline_output = script_util.runProgram(self.__LOGGER,"cuffmerge",cuffmerge_command,None,cuffmerge_dir)
	        #cmdline_output = script_util.runProgram(self.__LOGGER,"cuffmerge",cuffmerge_command,None,os.getcwd())
		if 'result' in cmdline_output:
			report = cmdline_output['result']	
            except Exception,e:
                raise KBaseRNASeqException("Error executing cuffmerge {0},{1},{2}".format(cuffmerge_command,cuffmerge_dir,e))
            
            ##  compress and upload to shock
            try:
                self.__LOGGER.info("Zipping Cuffmerge output")
		out_file_path = os.path.join(self.__SCRATCH,"{0}.zip".format(params['output_obj_name']))
                script_util.zip_files(self.__LOGGER,output_dir,out_file_path)
                #handle = hs.upload("{0}.zip".format(params['output_obj_name']))
            except Exception,e:
                raise KBaseRNASeqException("Error executing cuffmerge {0},{1}".format(os.getcwd(),e))
	    try:
		#out_file_path = os.path.join("{0}.zip".format(params['output_obj_name']))
		handle = hs.upload(out_file_path)
                #handle = script_util.create_shock_handle(self.__LOGGER,"%s.zip" % params['output_obj_name'],self.__SHOCK_URL,self.__HS_URL,"Zip",user_token)
                #if self.__PUBLIC_SHOCK_NODE is 'true': 
                #    script_util.shock_node_2b_public(self.__LOGGER,node_id=handle['id'],shock_service_url=handle['url'],token=user_token)
            except Exception, e:
                raise KBaseRNASeqException("Failed to upload the index: {0}".format(e))
	   
            #analysis['data']['transcriptome_id'] = "{0}/{1}".format(params["ws_id"], params['output_obj_name'])	
                # raise Exception(task_output["stdout"], task_output["stderr"])

	    ## Save object to workspace
	    try:
                self.__LOGGER.info("Saving Cuffmerge object to workspace")
                cm_obj = { 'file' : handle,
                           'analysis' : analysis['data']
                	 }
		#pprint(cm_obj)
            	res1= ws_client.save_objects(
                                        {"workspace":params['ws_id'],
                                         "objects": [{
                                         "type":"KBaseRNASeq.RNASeqCuffmergetranscriptome",
                                         "data":cm_obj,
                                         "name":params['output_obj_name']}
                                        ]})

                analysis['data']['transcriptome_id'] = "{0}/{1}".format(params["ws_id"], params['output_obj_name'])	
	        res= ws_client.save_objects(
                                        {"workspace":params['ws_id'],
                                         "objects": [{
                                         "type":"KBaseRNASeq.RNASeqAnalysis",
                                         "data":analysis['data'],
                                         "name":params['analysis']}
                                        ]})
			
	    except Exception, e:
                raise KBaseRNASeqException("Failed to upload the objects for Cuffmerge KBaseRNASeq.RNASeqAnalysis and KBaseRNASeq.RNASeqCuffmergetranscriptome: {0}".format(e))
	    returnVal = analysis['data'] 
	    #returnVal = { 'workspace' : params['ws_id'] , 'output' : params['analysis'] }
	except KBaseRNASeqException,e:
                 self.__LOGGER.exception("".join(traceback.format_exc()))
                 raise
	finally:
                 handler_util.cleanup(self.__LOGGER,cuffmerge_dir)
		 #if os.path.exists(out_file_path): os.remove(out_file_path)
        #END CuffmergeCall

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method CuffmergeCall return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

    def CuffdiffCall(self, ctx, params):
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN CuffdiffCall
	user_token=ctx['token']
	#pprint(params)
        self.__LOGGER.info("Started CuffdiffCall")

        ws_client=Workspace(url=self.__WS_URL, token=user_token)
        hs = HandleService(url=self.__HS_URL, token=user_token)
        try:
            #if os.path.exists(self.__SCRATCH):
            #    handler_util.cleanup(self.__LOGGER,self.__SCRATCH)
            if not os.path.exists(self.__SCRATCH): os.makedirs(self.__SCRATCH)
	    cuffdiff_dir = self.__SCRATCH +'/tmp'
            #cuffdiff_dir = self.__CUFFDIFF_DIR
            if os.path.exists(cuffdiff_dir):
                handler_util.cleanup(self.__LOGGER,cuffdiff_dir)
            if not os.path.exists(cuffdiff_dir): os.makedirs(cuffdiff_dir)

            self.__LOGGER.info("Downloading Analysis file")
            try:
                analysis = ws_client.get_objects(
                                        [{'name' : params['rnaseq_exp_details'],'workspace' : params['ws_id']}])[0]
            except Exception,e:
                 self.__LOGGER.exception("".join(traceback.format_exc()))
                 raise KBaseRNASeqException("Error Downloading objects from the workspace ")

            ## Downloading data from shock
            #list_file = open(self.__ASSEMBLY_GTF_FN,'w')
	    alignments  = []
	    sample_labels = []
            if 'data' in analysis : #and analysis['data'] is not None:
                self.__LOGGER.info("Downloading Sample Expression files")

                shock_re =  re.compile(r'^(.*)/node/([^?]*)\??')
                # TODO: Change expression_values object design
		le  = analysis['data']['alignments']
                #for le in analysis['data']['alignments']:
                for k,v in le.items():
                    ko,vo=ws_client.get_objects([{'ref' : k}, {'ref' : v} ])
                    #sp = os.path.join(cuffdiff_dir, ko['info'][1])
                    sp = os.path.join(cuffdiff_dir, ko['data']['metadata']['condition']+"/"+ko['data']['metadata']['replicate_id'])
		    #print sp 
                    if not os.path.exists(sp): os.makedirs(sp)
		    condition_id = ko['data']['metadata']['condition']
		    if not condition_id in sample_labels:
			sample_labels.append(condition_id)
                    if 'file' not in vo['data']:
                        self.__LOGGER.info("{0} does not contain file and we skip {1}".format(vo['info'][1], v))
                        next
		    se = vo['data']['file']['id']
		    se_url = vo['data']['file']['url']
		    efn = vo['data']['file']['file_name']
                    #se = shock_re.search(vo['data']['file'])
                    #if se is None:
                    #    self.__LOGGER.info("{0} does not contain shock_url and we skip {1}".format(vo['info'][1], v))
                    #    next

                    #efn = "{0}.zip".format(vo['info'][1])
	 	    try:
                         script_util.download_file_from_shock(self.__LOGGER, shock_service_url=se_url, shock_id=se,filename=efn, directory=cuffdiff_dir,token=user_token)
			 
                    except Exception,e:
                            raise Exception( "Unable to download shock file, {0}".format(e))
                    try:
                        script_util.unzip_files(self.__LOGGER,os.path.join(cuffdiff_dir,efn),sp)
                    except Exception, e:
                           raise Exception("Unzip indexfile error: Please contact help@kbase.us")
                    if not os.path.exists("{0}/accepted_hits.bam\n".format(sp)):
                       # Would it be better to be skipping this? if so, replace Exception to be next
                       next
		       #alignments.append("{0}/accepted_hits.bam ".format(sp))
                       #raise Exception("{0} does not contain transcripts.gtf:  {1}".format(vo['info'][1], v))
                    #list_file.write("{0}/transcripts.gtf\n".format(sp))
            else:
                raise KBaseRNASeqException("No data was included in the referenced analysis");
            	#list_file.close()

            ##  now ready to call
            output_dir = os.path.join(cuffdiff_dir, params['output_obj_name'])
	    #bam_files = " ".join([i for i in alignments])
	    for l in sample_labels:
		#for path, subdirs, files in os.walk(root):
       		#		os.path.join(path,"accepted_hits.bam")
		rep_files=",".join([ os.path.join(cuffdiff_dir+'/'+l,sub+'/accepted_hits.bam') for sub in os.listdir(os.path.join(cuffdiff_dir,l)) if os.path.isdir(os.path.join(cuffdiff_dir,l+'/'+sub))])
		alignments.append(rep_files) 
            
	    bam_files = " ".join([i for i in alignments])
	    #print bam_files
	    labels = ",".join(sample_labels)		
	    merged_gtf = analysis['data']['transcriptome_id']
	    try:
                transcriptome = ws_client.get_objects(
                                        [{ 'ref' : merged_gtf }])[0]
            except Exception,e:
                 self.__LOGGER.exception("".join(traceback.format_exc()))
                 raise KBaseRNASeqException("Error Downloading merged transcriptome ") 
	    t_url = transcriptome['data']['file']['url']
	    t_id = transcriptome['data']['file']['id']
	    t_name = transcriptome['data']['file']['file_name']
	    try:
                 script_util.download_file_from_shock(self.__LOGGER, shock_service_url=t_url, shock_id=t_id,filename=t_name, directory=cuffdiff_dir,token=user_token)

            except Exception,e:
                 raise Exception( "Unable to download transcriptome shock file, {0}".format(e))
            try:
                 script_util.unzip_files(self.__LOGGER,os.path.join(cuffdiff_dir,t_name),cuffdiff_dir)
            except Exception, e:
                 raise Exception("Unzip transcriptome zip file  error: Please contact help@kbase.us")
            gtf_file = os.path.join(cuffdiff_dir,"merged.gtf")
	   
            ### Adding advanced options
	    num_p = multiprocessing.cpu_count()
            #print 'processors count is ' +  str(num_p)
	    cuffdiff_command = (' -p '+str(num_p))
            #if('num-threads' in params and params['num-threads'] is not None) : cuffdiff_command += (' -p '+str(params['num-threads']))
	    if('time-series' in params and params['time-series'] != 0) : cuffdiff_command += (' -T ')
	    if('min-alignment-count' in params and params['min-alignment-count'] is not None ) : cuffdiff_command += (' -c '+str(params['min-alignment-count']))
	    if('multi-read-correct' in params and params['multi-read-correct'] != 0 ): cuffdiff_command += (' --multi-read-correct ')
	    if('library-type' in params and params['library-type'] is not None ) : cuffdiff_command += ( ' --library-type '+params['library-type'])
	    if('library-norm-method' in params and params['library-norm-method'] is not None ) : cuffdiff_command += ( ' --library-norm-method '+params['library-norm-method'])
 
	    try:
                # TODO: add reference GTF later, seems googledoc command looks wrong
                cuffdiff_command += " -o {0} -L {1} -u {2} {3}".format(output_dir,labels,gtf_file,bam_files)
		self.__LOGGER.info("Executing: cuffdiff {0}".format(cuffdiff_command))
                script_util.runProgram(self.__LOGGER,"cuffdiff",cuffdiff_command,None,cuffdiff_dir)
                #script_util.runProgram(self.__LOGGER,"cuffdiff",cuffdiff_command,None,os.getcwd())

            except Exception,e:
                raise KBaseRNASeqException("Error executing cuffdiff {0},{1},{2}".format(cuffdiff_command,cuffdiff_dir,e))

            ##  compress and upload to shock
            try:
                self.__LOGGER.info("Zipping Cuffdiff output")
		out_file_path = os.path.join(self.__SCRATCH,"{0}.zip".format(params['output_obj_name']))
                script_util.zip_files(self.__LOGGER,output_dir,out_file_path)
                #handle = hs.upload("{0}.zip".format(params['output_obj_name']))
            except Exception,e:
                raise KBaseRNASeqException("Error executing cuffdiff {0},{1}".format(os.getcwd(),e))
            try:
		#out_file_path = os.path.join("{0}.zip".format(params['output_obj_name']))
                handle = hs.upload(out_file_path)
            except Exception, e:
                raise KBaseRNASeqException("Failed to upload the Cuffdiff output files: {0}".format(e))


            ## Save object to workspace
            try:
		self.__LOGGER.info("Saving Cuffdiff object to workspace")
                cm_obj = { 'file' : handle,
                           'analysis' : analysis['data']
                	  }
                res1= ws_client.save_objects(
                                        {"workspace":params['ws_id'],
                                         "objects": [{
                                         "type":"KBaseRNASeq.RNASeqCuffdiffdifferentialExpression",
                                         "data":cm_obj,
                                         "name":params['output_obj_name']}
                                        ]})	
		
                analysis['data']['cuffdiff_diff_exp_id'] = "{0}/{1}".format(params['ws_id'],params['output_obj_name'])
		res= ws_client.save_objects(
                                        {"workspace":params['ws_id'],
                                         "objects": [{
                                         "type":"KBaseRNASeq.RNASeqAnalysis",
                                         "data":analysis['data'],
                                         "name":params['rnaseq_exp_details']}
                                        ]})
            except Exception, e:
                raise KBaseRNASeqException("Failed to upload the KBaseRNASeq.RNASeqCuffdiffdifferentialExpression and KBaseRNASeq.RNASeqAnalysis : {0}".format(e))

	    returnVal = analysis['data']
        except KBaseRNASeqException,e:
                 self.__LOGGER.exception("".join(traceback.format_exc()))
                 raise
	finally:
                 handler_util.cleanup(self.__LOGGER,cuffdiff_dir)
		 #if os.path.exists(out_file_path): os.remove(out_file_path)
        #END CuffdiffCall

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method CuffdiffCall return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

    def getAlignmentStats(self, ctx, params):
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN getAlignmentStats

	user_token=ctx['token']
        ws_client=Workspace(url=self.__WS_URL, token=user_token)        
	stats_dir = self.__STATS_DIR
        try:
            if os.path.exists(stats_dir):
            #   files=glob.glob("%s/*" % tophat_dir)
            #    for f in files: os.remove(f)
                handler_util.cleanup(self.__LOGGER,stats_dir)
            if not os.path.exists(stats_dir): os.makedirs(stats_dir)
        except Exception as e:
                raise KBaseRNASeqException("Couldn't prepare a folder, {0}, {1}".format(stats_dir, e))
	try:
                obj  = ws_client.get_objects([{'name' : params['alignment_sample_id'],'workspace' : params['ws_id'] }])[0]
        #return {"output" : str(status), "error": json_error}
        except Exception as e:
                raise KBaseRNASeqException("File Not Found: {}".format(e))
	#download Shock Node
	if 'data' in obj and obj['data'] is not None:
                self.__LOGGER.info("Downloading Sample Alignments")
                try:
                     script_util.download_file_from_shock(self.__LOGGER, shock_service_url=self.__SHOCK_URL, shock_id=obj['data']['file']['id'],
			 				filename=obj['data']['file']['file_name'], directory=stats_dir,token=user_token)
                except Exception,e:
                        raise Exception( "Unable to download shock file, {0}".format(e))
                try:
                    script_util.unzip_files(self.__LOGGER,os.path.join(stats_dir,obj['data']['file']['file_name']),stats_dir)
                    #script_util.move_files(self.__LOGGER,handler_util.get_dir(cufflinks_dir),cufflinks_dir)
                except Exception, e:
                       self.__LOGGER.error("".join(traceback.format_exc()))
                       raise Exception("Unzip file  error: Please contact help@kbase.us")
		#Create Command
 	        bam_file = stats_dir+"/accepted_hits.bam"
        	align_stats_cmd = "flagstat {0}".format(bam_file)
        else:
                raise KBaseRNASeqException("No data was included in the referenced sample id");
	
	# If Annotation is provided then run bedtools 
		
	if 'annotation_id' in params and params['annotation_id'] is not None:
		try:
                	annotation  = ws_client.get_objects([{'name' : params['annotation_id'],'workspace' : params['ws_id'] }])[0]
        	#return {"output" : str(status), "error": json_error}
        	except Exception as e:
                	raise FileNotFound("File Not Found: {}".format(e))
		if 'data' in annotation and annotation['data'] is not None:
               		self.__LOGGER.info("Downloading Reference Annotation")
                	try:
                     		script_util.download_file_from_shock(self.__LOGGER, shock_service_url=self.__SHOCK_URL, shock_id=annotation['data']['file']['id'],
                                                        filename=annotation['data']['file']['file_name'], directory=stats_dir,token=user_token)
                	except Exception,e:
                        	raise Exception( "Unable to download shock file, {0}".format(e))
                	try:
                    		script_util.unzip_files(self.__LOGGER,os.path.join(stats_dir,obj['data']['file']['file_name']),stats_dir)
                    #script_util.move_files(self.__LOGGER,handler_util.get_dir(cufflinks_dir),cufflinks_dir)
                	except Exception, e:
                       		self.__LOGGER.error("".join(traceback.format_exc()))
                       		raise Exception("Unzip file error: Please contact help@kbase.us")
            	else:
                	raise KBaseRNASeqException("No data was included in the annotation id");
		#Create Command
		bam_file = stats_dir+"/accepted_hits.bam"
		align_stats_cmd = "flagstat {0}".format(bam_file)
	
	#Run Command
        try:
                self.__LOGGER.info("Executing: samtools {0} {1}".format("samtools", align_stats_cmd))
		res = script_util.runProgram(self.__LOGGER,"samtools", align_stats_cmd,None,None)
        except Exception,e:
                raise KBaseRNASeqException("Error running samtools flagstat {0},{1}".format(bam_file,e))
		
	result = res['result']
        lines = result.splitlines()
        if  len(lines) != 11:
            raise KBaseRNASeqException("Error not getting enough samtool flagstat information: {0}".format(result))
        # patterns
        two_nums  = re.compile(r'^(\d+) \+ (\d+)')
        two_pcts  = re.compile(r'\(([0-9.na\-]+)%:([0-9.na\-]+)%\)')
        # alignment rate
        m = two_nums.match(lines[0])
        total_qcpr = int(m.group(1))
        total_qcfr = int(m.group(2))
        total_read =  total_qcpr + total_qcfr
    
        m = two_nums.match(lines[2])
        mapped_r = int(m.group(1))
        umapped_r = int(m.group(2))

        alignment_rate = mapped_r / total_read  * 100.0
        if alignment_rate > 100: alignment_rate = 100.0


        # singletons
        m = two_nums.match(lines[8])
        singletons = int(m.group(1))

        # multiple alignment : skip now
        m = two_nums.match(lines[6])
        properly_paired = int(m.group(1))
	# Create Workspace object
	stats_data =  { 
                       "alignment_id": params['alignment_sample_id'], 
                       "alignment_rate": alignment_rate, 
                       #"multiple_alignments": 50, 
                       "properly_paired": properly_paired, 
                       "singletons": singletons, 
                       "total_reads": total_read, 
                       "unmapped_reads": umapped_r,
                       "mapped_reads": mapped_r
                       }
	
	## Save object to workspace
        self.__LOGGER.info( "Saving Alignment Statistics to the Workspace")
        try:
		res= ws_client.save_objects(
                                        {"workspace":params['ws_id'],
                                         "objects": [{
                                         "type":"KBaseRNASeq.AlignmentStatsResults",
                                         "data": stats_data,
                                         "name":params['output_obj_name']}
                                        ]})
                returnVal = stats_data
        except Exception, e:
                raise KBaseRNASeqException("get Alignment Statistics failed: {0}".format(e))


        #END getAlignmentStats

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method getAlignmentStats return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

    def createExpressionHistogram(self, ctx, params):
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN createExpressionHistogram
	user_token=ctx['token']
        ws_client=Workspace(url=self.__WS_URL, token=user_token)
	
	try:
        	obj = ws_client.get_objects([{'name' : params['expression_sample'],'workspace' : params['ws_id'] }])[0]
        #return {"output" : str(status), "error": json_error}
    	except Exception as e:
        	raise FileNotFound("File Not Found: {}".format(e))
    	if 'expression_levels' in obj['data']:
        	hdict = obj['data']['expression_levels']
        	tot_genes =  len(hdict)
        	lmin = round(min([v for k,v in hdict.items()]))
        	lmax = round(max([v for k,v in hdict.items()]))
        	hist_dt = script_util.histogram(hdict.values(),lmin,lmax,int(params['number_of_bins']))
        	title = "Histogram  - " + params['expression_sample']
        	hist_json = {"title" :  title , "x_label" : "Gene Expression Level (FPKM)", "y_label" : "Number of Genes", "data" : hist_dt}
        	sorted_dt = OrderedDict({ "id" : "", "name" : "","row_ids" : [] ,"column_ids" : [] ,"row_labels" : [] ,"column_labels" : [] , "data" : [] })
        	sorted_dt["row_ids"] = [hist_json["x_label"]]
        	sorted_dt["column_ids"] = [hist_json["y_label"]]
        	sorted_dt['row_labels'] = [hist_json["x_label"]]
        	sorted_dt["column_labels"] =  [hist_json["y_label"]]
        	sorted_dt["data"] = [[float(i) for i in hist_json["data"]["x_axis"]],[float(j) for j in hist_json["data"]["y_axis"]]]
    		#sorted_dt["id"] = "kb|histogramdatatable."+str(idc.allocate_id_range("kb|histogramdatatable",1))
        	sorted_dt["id"] = params['output_obj_name']
        	sorted_dt["name"] = hist_json["title"]
        	res = ws_client.save_objects({"workspace": params['ws_id'],
                                  "objects": [{
                                                "type":"MAK.FloatDataTable",
                                                "data": sorted_dt,
                                                "name" : params['output_obj_name']}
                                            ]

                                 })
	#returnVal = { "workspace" : params['ws_id']  , "output" :  params['output_obj_name'] }
	returnVal = sorted_dt
        #END createExpressionHistogram

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method createExpressionHistogram return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]
