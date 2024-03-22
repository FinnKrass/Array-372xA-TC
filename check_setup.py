#!/usr/bin/env python
from typing import List,  Dict
import os, sys, re, csv

# Use with Testcontroller device config file for some cleaning and reporting (csv)
# This program will sort the #metadef and #cmdSetup commands/tags according to the given priority lists
# For # metadef some Caps checking is done
# The separator between :update: items can be customized
# The program creates a csv file separated by ";" for reporting and error checking
# Load it in excel (or equivalent) auto adjust column width and use the filter tool to select the rows based on column-1 (function) 
# On :update and :enable: it will check the control names of #cmdSetup
# Tag :tip: is reported based on the preferred & no tip lists, so you can see if you want to add or delete tip texts
# Selector entries are also checked and reported
# NOTE: this program makes a ew config file in the subdirectory "check"; you can see the changes with a compare program e.g. notepad++ addon

# developed with Python 3.9


def sort_by_priority_list(values: Dict[str,List[str]], priority: List[str]) -> Dict[str,List[str]]:
	# make dict of list by adding value as sequence number
	priority_dict = {k: i for i, k in enumerate(priority)}
	def use_priority_list(value):
		# get priority number for dict key; not found will return the lowest priority
		return priority_dict.get(value[0], len(priority_dict))
	return 	dict(sorted(values.items(), key=use_priority_list)) 

def process_meta_cmds(cmds: List[str], output_list: List[str]):
	cmd_dict: Dict[str,List[str]] = {}
	# create dict from list; split on first space
	# no space > value is blank
	# make list of values because duplicated key may exist
	for c in cmds:
		k:str = ''
		v:str = ''
		if (re.search(r'\s', c)):
			k, v = c.split(' ',1)
			k = k.lower()
			if k in cmd_dict:
				cmd_dict[k].append(v)
			else:
				cmd_dict[k] = [v]
		else:
			c = c.lower()
			if c in cmd_dict:
				cmd_dict[c].append('')
			else:
				cmd_dict[c] = ['']
		# do we have a non prioritised cmd?
		if (k[:1] == '#'):
			if (k not in meta_priority):
				print(f'Metadef cmd {k} is not in meta_priority list')
	# set the priority
	sort_result = sort_by_priority_list(cmd_dict, meta_priority)
	# convert dict with string list as value to list of strings
	for key in sort_result:
		index = key
		if key in to_caps:
			key = to_caps[index]
		for value in sort_result[index]:
			output_list.append(f"{key} {value}")


def process_setup_tags(tags: List[str],	cmdsetup:str, update_separator:str, 
											output_list: List[str], csv_list: List[List[str]], update_list: List[List[str]], selector_list: List[List[str]]):
	tag_dict: Dict[str,List[str]] = {}
	# get cs_item on: #cmdsetup  control-type control-name page-name
	#             	> cs_item[0] cs_item[1]   cs_item[2]   cs_item[3]  
	cs_item: List[str] = cmdsetup.split()
	if len(cs_item) == 3:
		cs_item.append('unpaged setup')
	# are we expecting a :tip: tag?
	tip_must_be_present: bool = False
	tip_must_be_absent: bool = False
	tip_present: bool = False
	if cs_item[1].lower() in no_tip:
		tip_must_be_absent = True
	if cs_item[1].lower() in preferred_tip:
		tip_must_be_present = True
	# create dict from list; split on first space
	# no space > value is blank
	# make list of values because duplicated key may exist
	for t in tags:
		k_lower:str = ''
		t_lower:str = ''
		k:str = ''
		v:str = ''
		if (re.search(r'\s', t)):
			k, v = t.split(' ',1)
			k_lower = k.lower()
			#cleanup comma vs space separation on :update:
			if (k_lower == ':update:'):
				v = v.replace(',',' ')
				v = update_separator.join(v.split())
			if k_lower in tag_dict:
				tag_dict[k_lower].append(v)
			else:
				tag_dict[k] = [v]
		else:
			t_lower = t.lower()
			if t_lower in tag_dict:
				tag_dict[t_lower].append('')
			else:
				tag_dict[t] = ['']
			k = t
			k_lower = t_lower
		# process selector entries, skip cmds & comments
		if (cs_item[1] == 'selector'):
			if not re.match(r'[:;]', k):
				controls = v.split()
				for cntrl in controls:
					if '.' in cntrl:
						p_name, c_name = cntrl.split('.',1)
						selector_list.append([p_name, c_name, k, cs_item[3], cs_item[2]])
					elif (cs_item[3] == 'unpaged setup'):
						selector_list.append(['unpaged setup', cntrl, k, cs_item[3], cs_item[2]])
					else:	
						csv_list.append(['warning', cs_item[3], cs_item[2], cs_item[1], 'No page.control construct found in', cntrl])
		# do we have a non prioritised tag?
		if (k_lower[:1] == ':'):
			if (k_lower not in setup_priority):
				print(f'Tag {k} on {cmdsetup} is not in setup_priority list')
		# make list of :update:, :enable: and :tip: tags
		if (k_lower == ':update:'):
			if(v != ''):
				v = v.replace(',',' ')
				# every control on :update: in a separate csv record
				names = v.split()
				for name in names:
					if '.' in name:
						csv_list.append(['warning', cs_item[3], cs_item[2], cs_item[1], 'possible page-name in', name])	
					update_list.append([cs_item[3], cs_item[2], cs_item[1], name])
			else:
				csv_list.append(['warning', cs_item[3], cs_item[2], cs_item[1], 'has empty update tag'])		
		elif (k_lower == ':enable:'):
			# currenty no checking on validity of control names
			if(v != ''):
				csv_list.append(['enable', cs_item[3], cs_item[2], cs_item[1], 'is enabled when', v,'is true'])
			else:
				csv_list.append(['warning', cs_item[3], cs_item[2], cs_item[1], 'has empty enable tag'])
		elif (k_lower == ':tip:'):
			# value present
			if (v != ''):
				tip_present = True
				if (tip_must_be_absent):
					csv_list.append(['tip', cs_item[3], cs_item[2], cs_item[1], '[WARN] tip preferable absent, but tip found', v])
				else:
					csv_list.append(['tip', cs_item[3], cs_item[2], cs_item[1], '[OK] tip is', v])
			# value blank
			else:
				if (tip_must_be_present):
					csv_list.append(['tip', cs_item[3], cs_item[2], cs_item[1], '[WARN] tip preferred, but tip tag without text found'])
				elif (tip_must_be_absent):
					csv_list.append(['tip', cs_item[3], cs_item[2], cs_item[1], '[WARN] empty tip tag found,  but should be absent'])
				else:
					csv_list.append(['tip', cs_item[3], cs_item[2], cs_item[1], '[WARN] tip tag without text found'])
	# ready with this cmdsetup > check status of :tip: when not found
	if (not tip_present):
		if (tip_must_be_present): 
			csv_list.append(['tip', cs_item[3], cs_item[2], cs_item[1], '[WARN] tip preferred, but tip tag not found'])
		elif (tip_must_be_absent):
			csv_list.append(['tip', cs_item[3], cs_item[2], cs_item[1], '[OK] tip preferable absent and not found'])
		else:
			csv_list.append(['tip', cs_item[3], cs_item[2], cs_item[1], '[OK] tip not found'])
	# set the priority
	sort_result = sort_by_priority_list(tag_dict, setup_priority)
	# convert dict with string list as value to list of strings
	for key in sort_result:
		for value in sort_result[key]:
			if value == '':
				output_list.append(f"{key}")
			else:
				output_list.append(f"{key} {value}")


def main():
	cfg_input: List[str] = []
	output_list: List[str] = []
	csv_list: List[List[str]] = []
	cmd_lines: List[str] = []
	tag_lines: List[str] = []
	comment_lines: List[str] = []
	saved_cmdsetups: List[str] = []
	update_list: List[List[str]] = []
	selector_list: List[List[str]] = []
	saved_metadef: str = '' 
	first_metadef: bool = False
	skip_metadef: bool = False
	saved_cmdsetup: str = '' 
	first_cmdsetup: bool = False
	cs_found: bool = False
	if (len(sys.argv) < 2):
		print('Usage: check_setup.py input_config_file')
		sys.exit(1)
	if (not os.path.isfile(sys.argv[1])):
		print(f'Input file {sys.argv[1]} does not exist.')
		sys.exit(1)
	input_match = re.match(r"(.*[\\\/]|)(.*).txt$",sys.argv[1], re.IGNORECASE) 
	if (not input_match):
		print(f'Input file {sys.argv[1]} is not a .txt file.')
		sys.exit(1)
	[input_dir_name, input_file_name] = input_match.group(1, 2)
	new_dir_name = input_dir_name + 'check'
	if (not os.path.isdir(new_dir_name)):
		os.mkdir(new_dir_name)
	filename = new_dir_name + '/' + input_file_name
	# open output files
	with open(f"{filename}.txt", 'w', encoding='UTF8') as fo, open(f"{filename}.csv", 'w', encoding='UTF8', newline='') as fc:
		csv_writer = csv.writer(fc, delimiter =';')
		# read config file
		with open(sys.argv[1], encoding='utf-8') as f:
			try:
				cfg_input = f.readlines()
			except:
				print(f'Could not process input file {sys.argv[1]}')
			# check config file
			line_count: int = 0
			for line in cfg_input:
				line_count += 1
				line = line.strip()
				# stop with #metadef when #meta has been found
				if (skip_metadef == False):
					#process #metadef
					if (first_metadef == False):
						# first #metadef found
						if (re.match(r'#metadef', line, re.I)):
							saved_metadef = line
							first_metadef = True 
						# everything before first #metadef
						else:
							output_list.append(line)
					# next #metadef found
					elif (re.match(r'#metadef', line, re.I)):
						output_list.append(saved_metadef)
						process_meta_cmds(cmd_lines, output_list)
						for c in comment_lines:
							output_list.append(c)
						saved_metadef = line
						cmd_lines = []
						comment_lines = []
					# empty lines and comment lines
					elif (re.match(r'\s*$', line) or re.match(r';', line)):
						comment_lines.append(line)
					# #meta found; close #metadef processing
					elif (re.match(r'#meta$', line, re.I)):
						skip_metadef = True
						output_list.append(saved_metadef)
						process_meta_cmds(cmd_lines, output_list)
						for c in comment_lines:
							output_list.append(c)
						cmd_lines = []
						comment_lines = []
						output_list.append(line)
					# check line for #metadef commands	
					else:
						if (re.search(r'\s', line)):
							cmd = line.split(' ',1)[0]
							cmd = cmd.lower()
						else:
							cmd = line.lower()
						# other #metadef commands found?
						if cmd in meta_priority:
							cmd_lines.append(line)
							# comment lines in between #metadef commands are saved
							# and are put in the order given by the priority list
							# empty lines are omitted 
							if (len(comment_lines) > 0):
								for c in comment_lines:
									if (re.match(r';', c)):
										tag_lines.append(c)
									comment_lines = []
						else:
							comment_lines.append(line)
				# process #cmdsetup
				else:
					if (first_cmdsetup == False):
						# first #cmdsetup command found
						if (re.match(r'^#cmdsetup ', line, re.I)):
							saved_cmdsetup = line
							first_cmdsetup = True
						# everything before first #cmdsetup command
						else:
							output_list.append(line)
					# next #cmdsetup found
					else:
						if (re.match(r'#cmdsetup', line, re.I)):
							output_list.append(saved_cmdsetup)
							saved_cmdsetups.append(saved_cmdsetup)
							process_setup_tags(tag_lines, saved_cmdsetup, update_separator, output_list, csv_list, update_list, selector_list)
							for c in comment_lines:
								output_list.append(c)
							saved_cmdsetup = line
							tag_lines = []
							comment_lines = []
						# empty lines and comment lines
						elif (re.match(r'\s*$', line) or re.match(r';', line)):
							comment_lines.append(line)
						# tags & other # cmdsetup lines found
						else:
							tag_lines.append(line)
							# comment lines in between #cmdsetup lines are saved
							# and are put in the order given by the priority list
							# empty lines are omitted 
							if (len(comment_lines) > 0):
								for c in comment_lines:
									if (re.match(r';', c)):
										tag_lines.append(c)
									comment_lines = []
					# don't forget the last #cmdsetup
					if (line_count == len(cfg_input)):
							output_list.append(saved_cmdsetup)
							saved_cmdsetups.append(saved_cmdsetup)
							process_setup_tags(tag_lines, saved_cmdsetup, update_separator, output_list, csv_list, update_list, selector_list)
							for c in comment_lines:
								output_list.append(c)
							saved_cmdsetup = line
							tag_lines = []
							comment_lines = []
			# make list of all setup controls
			for cmdsetup in saved_cmdsetups:
				cs_item = cmdsetup.split()
				if len(cs_item) == 3:
					cs_item.append('unpaged setup')
				csv_list.append(['info', cs_item[3], cs_item[2], cs_item[1], 'cmdsetup found'])
			# make list of setup controls which are updated
			for update in update_list:
				cs_found = False
				cs_item = []
				for cmdsetup in saved_cmdsetups:
					cs_item = cmdsetup.split()
					if len(cs_item) == 3:
						cs_item.append('unpaged setup')
					if update[3] == cs_item[2]:
						csv_list.append(['update', update[0], update[1], update[2], 'updates', cs_item[3], cs_item[2], cs_item[1]])
						cs_found = True
				if(cs_found == False):	
					csv_list.append(['update', update[0], update[1], update[2], 'tries update of', update[3], ', but not found'])
			# make list of setup controls which are on selectors
			for selector in selector_list:
				cs_found = False
				for cmdsetup in saved_cmdsetups:
					cs_item = cmdsetup.split()
					if len(cs_item) == 3:
						cs_item.append('unpaged setup')
					if (selector[1] == cs_item[2] and selector[0] == cs_item[3]):
						csv_list.append(['selector', selector[0], selector[1], '', f"in entry {selector[2]} of", selector[3], selector[4]])
						cs_found = True
				if(cs_found == False):	
					csv_list.append(['selector', selector[0], selector[1], '', f"in entry {selector[2]} of", selector[3], selector[4], 'not found'])
			# create content of output files
			for entry in output_list:
					fo.write(f"{entry}\n")
			print(f"Created output file: {filename}.txt")
			csv_writer.writerow(['function','page-name','control-name','control-type','comment/action','page-name/tag-value','control-name/comment','control-type/comment'])
			for entry in csv_list:
				csv_writer.writerow(entry)
			print(f"Created csv file: {filename}.csv")


if __name__ == '__main__':
	# order in priority lists sets the order for the output in the config file; ONLY USE LOWER CASE
	# note: meta_priority is only for #metadef commands
	meta_priority: List[str] = ['#metadebug', ';', '#idstring', '#name', '#handle', 
															'#port', '#driver', '#baudrate', '#subdriver', 
															'#replace', '#replacetext', '#remove', '#removeline','#sections'] 
	setup_priority: List[str] = [';', ':read:', ':readmath:', ':readformat:', ':write:', ':emptywrite:', ':update:', 
															':updatedelayed:', ':updatealloff:', ':updatemodechange:', ':enable:', 
															':tip:', ':buttontext:', ':textwidth:', ':color:',':string:', ':emptyfield:']
	# convert commands from all lowercase to:
	to_caps: Dict[str,str] = {'#metadebug':'#metaDebug', '#idstring':'#idString',
														'#replacetext':'#replaceText', '#removeline':'#removeLine'}
	# list of #cmdSetup command that should normally have a text in :tip: tag; ONLY USE LOWER CASE
	preferred_tip: List[str] = ['number', 'numberint', 'numberdual', 'multi', 'text' ]
	# list of #cmdSetup command that should normally have no :tip: tag; ONLY USE LOWER CASE
	no_tip: List[str] =        ['selector','color', 'info', 'button', 'buttonson']
	# control name separator on :update: tag
	update_separator: str = ' '
	main()
 