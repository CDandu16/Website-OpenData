import cyclone.web
import sys
import os

from twisted.internet import reactor
from twisted.python import log

from mako import exceptions
from mako.template import Template
from mako.lookup import TemplateLookup


# Postgresql Password = Password
# Port = 5432


root = os.path.join(os.path.dirname(__file__), ".")

db   = "http://127.0.0.1:5432"

version = "0.0.1"

lookup = TemplateLookup(directories=[os.path.join(root, 'views')],
						input_encoding='utf-8',
						output_encoding="utf-8",
						default_filters=['decode.utf-8'],
						module_directory=os.path.join(root, 'tmp/mako'))






class MainHandler(cyclone.web.RequestHandler):
    def get(self):
        self.write(renderTemplate("home.html"))

class LoginHandler(cyclone.web.RequestHandler):
	def get(self):
		self.write(renderTemplate("login.html"))

class AboutHandler(cyclone.web.RequestHandler):
	def get(self):
		self.write(renderTemplate("about.html"))

class AccountRegisterHandler(cyclone.web.RequestHandler):
	def get(self):
		self.write(renderTemplate("register.html"))

class PasswordResetHandler(cyclone.web.RequestHandler):
	def get(self):
		self.write(renderTemplate("password-reset.html"))



def renderTemplate(templateName, **kwargs):
	template = lookup.get_template(templateName)
	args = []
	kwargs['version'] = version
	try:
		return template.render(*args, **kwargs)
	except Exception, e:
		print e

if __name__ == "__main__":


	# The format for adding is this:
	# (r"/requestSentToServer", ClassNameToCall)
	application = cyclone.web.Application([

	    (r"/", MainHandler),
	    (r"/login", LoginHandler),
	    (r"/about", AboutHandler),
	    (r"/register", AccountRegisterHandler),
	    (r"/password-reset", PasswordResetHandler),

	    (r"/static/(.*)", cyclone.web.StaticFileHandler, {"path": os.path.join(root, "static")})
	])

	log.startLogging(sys.stdout)
	reactor.listenTCP(8888, application)
	reactor.run()