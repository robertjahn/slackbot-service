# -*- coding: utf-8 -*-

from slackbot.bot import respond_to
import re
import json
import requests
import datetime
import os
import time
import logging
import slackbot_settings

keptn_host = os.getenv('keptn_host')
keptn_token = os.getenv('keptn_api_token')
headers = {'x-token': keptn_token, 'Content-Type': 'application/json'}

def helper_datetime(mins):
	past = datetime.datetime.now() - datetime.timedelta(minutes=int(mins))
	return past.isoformat()

def send_event(start, end, project, service, stage):
	
	body = {
  		"data": {
    	"start": start,
    	"end": end,
    	"project": project,
    	"service": service,
    	"stage": stage,
    	"teststrategy": "manual"
  		},
  		"type": "sh.keptn.event.start-evaluation"
	}
	res = requests.post(url=keptn_host+"/v1/event", headers=headers, data=json.dumps(body), verify=slackbot_settings.TRUST_SELFSIGNED_SSL)
	res_json = res.json()
	keptn_context = res_json['keptnContext']
	token = res_json['token']

	return keptn_context

def get_evaluation(keptn_context, message):
	url = '{0}/v1/event?keptnContext={1}&type=sh.keptn.events.evaluation-done'.format(keptn_host, keptn_context)
	
	res_json = None
	
	# 1 minute timeout until status code is 200
	res_timeout = time.time() + slackbot_settings.EVALUATION_TIMEOUT*1 
	while res_timeout > time.time():
		res = requests.get(url=url, headers=headers, verify=slackbot_settings.TRUST_SELFSIGNED_SSL)
		if(res.status_code == 200):
			res_json = res.json()
			break
		time.sleep(1)
	
	# indicator results
	indicators = json.dumps(res_json['data']['evaluationdetails'])
	
	message.send_webapi("Evaluation-Done", attachments = [
        {
	    "blocks": [
	    	{
	    		"type": "divider"
	    	},
	    	{
	    		"type": "section",
	    		"fields": [
	    			{
	    				"type": "mrkdwn",
	    				"text": "*Project:*\n " + res_json['data']['project']
	    			},
	    			{
	    				"type": "mrkdwn",
	    				"text": "*Service:*\n " + res_json['data']['service']
	    			},
					{
	    				"type": "mrkdwn",
	    				"text": "*Stage:*\n " + res_json['data']['service']
	    			},
					{
	    				"type": "mrkdwn",
	    				"text": "*Strategy:*\n " + res_json['data']['teststrategy']
	    			},
	    			{
	    				"type": "mrkdwn",
	    				"text": "*Time:*\n " + res_json['time']
	    			},
	    			{
	    				"type": "mrkdwn",
	    				"text": "*Result:*\n " + res_json['data']['result']
	    			},
	    			{
	    				"type": "mrkdwn",
	    				"text": "*shkeptncontext:*\n " + res_json['shkeptncontext']
	    			}
	    		]
	    	},
	    	{
	    		"type": "divider"
	    	}
	            ]
        }
    ])
	message.reply(indicators, in_thread=True)


@respond_to(r'start-evaluation (.*)', re.IGNORECASE)
def start_evaluation(message, args):
	try:
		args_list = args.split(' ')
		project, service, stage, start_datetime, end_datetime = '','','','',''
		print(args_list)
		if(len(args_list) == 4):
			project = args_list[0]
			service = args_list[1]
			stage = args_list[2]
			end_datetime_dt = datetime.datetime.now()
			end_datetime = end_datetime_dt.isoformat()
			start_datetime = (end_datetime_dt - datetime.timedelta(minutes=int(args_list[3]))).isoformat()
		elif(len(args_list) == 5):
			project = args_list[0]
			service = args_list[1]
			stage = args_list[2]
			start_datetime = args_list[3]
			end_datetime = args_list[4]
		elif(len(args_list) == 0 or len(args_list) < 5):
			now = datetime.datetime.now().isoformat()
			message.reply("`Message should be like: start-evaluation <project> <service> <stage> <start> <end> | start and end should be in iso format i.e {}`".format(now))
			return
		
		strategy = 'manual' # args_list[3]

    	# call keptn API send event
		logging.info("Project: " + project)
		logging.info("Service: " + service)
		logging.info("Stage: " + stage)
		logging.info("Strategy: " + strategy)
		logging.info("Start: " + start_datetime)
		logging.info("End: " + end_datetime)
		
		keptn_context = send_event(start_datetime, end_datetime, project, service, stage)

		message.send_webapi("Start-Evaluation", attachments = [
        {
	    "blocks": [
	    	{
	    		"type": "divider"
	    	},
	    	{
	    		"type": "section",
	    		"fields": [
	    			{
	    				"type": "mrkdwn",
	    				"text": "*Project:*\n " + project
	    			},
	    			{
	    				"type": "mrkdwn",
	    				"text": "*Service:*\n " + service
	    			},
					{
	    				"type": "mrkdwn",
	    				"text": "*Stage:*\n " + stage
	    			},
					{
	    				"type": "mrkdwn",
	    				"text": "*Strategy:*\n " + strategy
	    			},
	    			{
	    				"type": "mrkdwn",
	    				"text": "*Start:*\n " + start_datetime
	    			},
	    			{
	    				"type": "mrkdwn",
	    				"text": "*End:*\n " + end_datetime
	    			},
	    			{
	    				"type": "mrkdwn",
	    				"text": "*Keptn Context:*\n " + keptn_context
	    			}
	    		]
	    	},
	    	{
	    		"type": "divider"
	    	}
	            ]
        }
    	])
		
	except Exception as e:
		logging.error(e)


	# loops over until it gets response
	try:
		get_evaluation(keptn_context, message)
	except Exception as e:
		message.send('`Something went wrong!`')
		logging.error(e)