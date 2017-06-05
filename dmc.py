import sublime
import os, sys
import string

from Default.exec import ProcessListener
from Default.exec import ExecCommand

class DmcCommand(ExecCommand, ProcessListener):
	dream_daemon = None
	dream_seeker = None

	#DreamMaker
	proc 	     = None
	quiet 		 = False

	def run(
    		self,
            cmd=None,
            shell_cmd=None,
            file_regex="",
            line_regex="",
            working_dir="",
            encoding="utf-8",
            env={},
            quiet=False,
            kill=False,
            update_phantoms_only=False,
            hide_phantoms_only=False,
            word_wrap=True,
            syntax="Packages/Dream Maker/Dream Maker.tmLanguage",
            # Catches "path" and "shell"
            task = "",
            kill_old = False,
            **kwargs
            ):

		# get file from arguments and make it an absolute path
		file = cmd[0]
		os.path.abspath(file)

		sublime.status_message("Locating DME file...")
		dme_file = self.climb_to_ext(file, '.dme')
		dme_dir = None
		if dme_file == None:
			dme_file = file
			dme_dir = os.path.dirname(dme_file)
		else:
			dme_dir = os.path.dirname(dme_file)

		#override build process if we are just modifying the dme includes
		if task == 'add' or task == 'remove':
			self.modify_dme_includes(file,dme_file,task)
			return
			
		# override the cmd list depending on the task we want to perform
		dme = os.path.split(dme_file)[1]
		if task == 'seeker' or task == 'daemon':
			cmd[0] = os.path.splitext(dme)[0] + '.dmb'
		else:
			cmd[0] = dme

		sublime.status_message("Locating BYOND software...")
		exe = 'DreamMaker'
		if task == 'seeker':
			exe = 'DreamSeeker'
		elif task == 'daemon':
			exe = 'DreamDaemon'
		cmd.insert(0,self.locate_binaries(exe))
		
		if kill_first == True:
			super(DmcCommand,self).run(
				cmd, shell_cmd, file_regex, line_regex, dme_dir, encoding, env,
				quiet, True, update_phantoms_only, hide_phantoms_only, word_wrap,
				syntax, **kwargs)
			kill = False
		
		return super(DmcCommand,self).run(
            cmd, shell_cmd, file_regex, line_regex, dme_dir, encoding, env,
            quiet, kill, update_phantoms_only, hide_phantoms_only, word_wrap,
            syntax, **kwargs)
	

	# helpers
	def climb_to_ext(self, start, ext):
		# get root directory for path tree climb bounds
		root = None
		if os.name == 'nt':
			root = os.path.splitdrive(start)[0]+"\\"
		elif os.name == 'posix':
			root = '/'

		# climb up path searching each directory for a file with specified ext
		end = None
		cd = os.path.dirname(start)
		max_iter = 10
		while --max_iter and cd != root:
			for node in os.listdir(cd):
				if os.path.splitext(node)[1] == ext:
					return os.path.join(cd,node)
			cd = os.path.dirname(cd)

		return None

	def locate_binaries(self, exe):
		dirs = os.path.defpath.split(os.pathsep)
		if os.name == 'nt':
			if exe == 'DreamMaker':
				exe = 'dm.exe'
			else:
				exe += '.exe'
			# search in %PROGRAMFILES%
			root = os.path.expandvars('%PROGRAMFILES%')
			if os.path.isdir(root+' (x86)') == True:
				root += ' (x86)'
			dirs = os.listdir(root)

			for cd in dirs:
				x = os.path.join(root,cd,'bin',exe)
				if os.path.isfile(x):
					return x
		else:
			for cd in dirs:
				x = os.path.join(cd,exe)
				if os.path.isfile(x):
					return x

		return exe

	def modify_dme_includes(self, file, dme_file, task):
		sublime.status_message('Modifying DME...')
		file_rel = os.path.relpath(file,os.path.dirname(dme_file))
		if(os.path.splitext(dme_file)[1] != '.dme'):
			sublime.status_message('Cannot modify DME:'+os.path.split(dme_file)[1])
			return
		if(os.path.splitext(file)[1] == '.dme'):
			sublime.status_message('Cannot add \''+file_rel+'\' file to DME.')
			return

		# split the file into a header
		part = open(dme_file,'r').read().partition('// BEGIN_INCLUDE\n')
		header = part[0] + part[1]
		
		# a footer
		part = part[2].partition('// END_INCLUDE\n')
		footer = part[1] + part[2]

		# and split the includes section into a list
		includes = part[0].splitlines()

		# replace slashes with backslashes as byond uses windows paths
		file_rel = file_rel.replace('/','\\')
		
		# search includes for our relative path.
		index = -1
		modified = False

		for line in includes:
			index += 1
			if line.find(file_rel) > -1:
				if task == 'remove':
					includes.pop(index)
				modified = True
				break
		# if not in includes append to the end and then sort
		if modified == False and task == 'add':
			includes.append('#include \"'+file_rel+'\"')
			includes.sort(key=self.sort_key)
			modified = True
		
		open(dme_file,'w').write(header + '\n'.join(includes)+'\n' + footer)

		if modified == True:
			if task == 'add':
				sublime.status_message('Added file to '+os.path.split(dme_file)[1]+': '+file_rel)
			else:
				sublime.status_message('Removed file from '+os.path.split(dme_file)[1]+': '+file_rel)
		return 

	# ensures subdirectories are placed after files
	def sort_key(self,key):
		return key.replace('\\','~\\',key.count('\\')-1)
