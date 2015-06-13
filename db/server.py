# import pdb

# import os
# import time
# import re
# import base64
# import sys
# import json
# import datetime
# import math
# import logging
# import traceback
# import yaml
# import argparse


import psycopg2
from psycopg2 import extras

import cyclone.web
import cyclone.httpclient
from cyclone.bottle import run, route
from cyclone.httpclient import fetch

from twisted.internet import reactor
from twisted.internet import defer
from twisted.internet import ssl
from twisted.python import log
from twisted.python.logfile import DailyLogFile

from mako import exceptions
from mako.template import Template
from mako.lookup import TemplateLookup

# The dictionary containing environment information
env = {}

# The printed version of the website.
version = "1.2.5"

# The root directory of the server - this file
root = os.path.join(os.path.dirname(__file__), ".")

# Connect to a local database
'''
Replace [database] [user] [password] [host] and [port] with data specific to your postgreSQL setup
If you followed the install guide it should be 'safevisitor', 'postgres', [whatever you set the password to be], 'localhost', '5432'
If you are connected to the database via PGadmin3, right click on the server and all this information will be available
'''
conn = psycopg2.connect(database="MoTown", user="postgres", password="hack4detroit", host="127.0.0.1", port="5432")


#returns a list of all clients
class getAllClientsHandler(cyclone.web.RequestHandler):
	def post(self):
			curr=conn.cursor()
			curr.execute('SELECT * FROM "getAllClients"();')
			#TODO break down clients into a dictionary containging each element it 
			#holds so server.py does not need to know the array structure
			clients = curr.fetchall()
			self.write(json.dumps({"clients":clients}, separators=(', ',': ')))

##
# This class logs a user into the database and gets their session information
class LoginHandler(cyclone.web.RequestHandler):
	def post(self):
		args = convertRequestArgs(self.request.arguments)
		
		# log the user in and get the session id
		curr=conn.cursor()
		SQL = 'SELECT * FROM "userLogin"(%s, %s);'
		vals = [args['userID'], args['buildingID']]
		execSQL(curr, SQL, vals)
		results = curr.fetchone()
		conn.commit()
		curr.close()
		
		print results

		userData = {"sessionID": results[0]}
		self.write(json.dumps(userData, separators=(', ', ': ')))

##
# This class logs a visitor out of the database
class SignoutVisitorHandler(cyclone.web.RequestHandler):
	def post(self):
		args = convertRequestArgs(self.request.arguments)
		
		# log the visitor out
		curr=conn.cursor()
		SQL = 'SELECT * FROM "signOutVisitor"(CAST(%s AS INT));'
		vals = [args['visitorID']]

		curr.execute(SQL, vals)
		results = curr.fetchone()

		conn.commit()
		curr.close()

		if results is not None:
			visitorData = {"id": results[0], "fname": results[1], "mname": results[2], "lname": results[3]}
		else:
			visitorData = {"id": -1, "fname": -1, "mname": -1, "lname": -1}

		self.write(json.dumps(visitorData, separators=(',', ':')))

##
#this takes in a userID as an argument and removes that user
#from the users table
class DeleteUserHandler(cyclone.web.RequestHandler):
	def post(self):

		args = convertRequestArgs(self.request.arguments)
		curr=conn.cursor()
		SQL = 'SELECT "deleteBuildingContactsByUID"(%s);'
		vals = [args['userID']]
		curr.execute(SQL, vals)
		conn.commit()
		curr.close()

		curr=conn.cursor()
		SQL = 'SELECT "deleteBuildingAttendantsByUID"(%s);'
		curr.execute(SQL, vals)
		conn.commit()
		curr.close()		

		curr=conn.cursor()
		SQL = 'SELECT "deleteUser"(%s);'
		curr.execute(SQL, vals)
		conn.commit()
		curr.close()


##
#This class adds a user to the database and returns whether or not it was successful
class AddUserHandler(cyclone.web.RequestHandler):
	def post(self):
		args = convertRequestArgs(self.request.arguments)

		salt, digest = hasher.getDigest(args['password'])
	
		curr=conn.cursor()
		SQL = 'SELECT * FROM "addUser"(CAST(%s AS INT), CAST(%s AS INT), CAST(%s AS TEXT), CAST(%s AS TEXT), CAST(%s AS TEXT), CAST(%s AS TEXT), CAST(%s AS TEXT), CAST(%s AS TEXT))'
		vals = [args['clientID'], args['role'], args['username'].lower(), args['fname'], args['lname'], args['email'], digest, salt]; #put values her
		execSQL(curr, SQL, vals)
		result = curr.fetchone()

		conn.commit()
		curr.close()

		self.write(json.dumps({"userAdded":result}, separators=(', ', ': ')))

##
# Formats the given error text to an html form, pastes in the current stack trace, and returns it as a string
def formatStackTraceToHtml(errorText):
	return errorText + '<br></br><br>Stack trace:</br><br>' + '</br><br>'.join(traceback.format_stack()[:-1]) + '</br><br>**note that the error is not in this last line, this is just the point where the error was detected and renderErrorPage() was called</br>'

##
# Formats the given error text, pastes in the current stack trace, and returns it for printing
def formatStackTraceToText(errorText):
	return 'ERROR: ' + errorText + '\nStack trace:\n' + ''.join(traceback.format_stack()[:-1]) + '**note that the error is not in this last line, this is just the point where the error was detected and log.msg() was called\n'

##
# Replaces all newlines with page breaks so it displays correctly when pasted in an html document
def formatErrorTextToHtml(errorText):
	return '<br>' + errorText.replace('\n', '</br></br>') + '</br>'


##		
# cyclone.web.RequestHandler.arguments is a dictionary with array values, this extracts the strings 
def convertRequestArgs(args):
	for key in args:
		args[key] = args[key][0]
	return args

##
# A convenience function for calling the sql curr.exec
# function with proper error handling for failed SQL commands.
# This should prevent the DB from entering a bad state on
# a failed command by rolling back any failed transactions.
def execSQL(curr, SQL, vals):
	try:
		curr.execute(SQL, vals)
	except (psycopg2.DataError, psycopg2.InternalError, Exception) as e:
		log.msg("ERROR: A psycopg error occurred = " + str(e))
		errorText = "Problem interacting with the Safehiring database\n\nError: " +  str(e)
		renderErrorPage(formatErrorTextToHtml(errorText))

		# Rollback the transaction
		conn.rollback()


if __name__ == "__main__":


	# The format for adding is this:
	# (r"/requestSentToDatabase", ClassNameToCall)
	application = cyclone.web.Application([

	   	(r"/login", LoginHandler),
		(r"/signout", SignoutVisitorHandler),

	    (r"/static/(.*)", cyclone.web.StaticFileHandler, {"path": os.path.join(root, "static")})
	])

	log.startLogging(sys.stdout)
	reactor.listenTCP(5432, application)
	reactor.run()
