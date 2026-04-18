#discord_quote.py
#Copyright 2026 Alice Averlong
#This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free 
# Software Foundation, either version 3 of the License, or (at your option) 
# any later version.
#This program is distributed in the hope that it will be useful, but WITHOUT 
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#You should have received a copy of the GNU General Public License along with 
# this program. If not, see <https://www.gnu.org/licenses/>. 

import argparse, re

DEFAULT_RIGHT_USER = 'Alice Averlong'

MONTH_NAMES=['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
MONTHS='(?P<month>{})'.format('|'.join(MONTH_NAMES))
MONTH_DICT = dict([(name,1+i) for (i,name) in enumerate(MONTH_NAMES)])

WEEKDAYS='(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)'

alice_style_username_short_line_re=re.compile(
	r'^\[(?P<time>\d{1,2}:\d{2}(?: [AP]M)?)\]'+
	WEEKDAYS+
	', '+MONTHS+r' (?P<day>\d{1,2}), (?P<year>\d{4}) (?P=time)'
)

alice_style_username_full_line_re=re.compile(
	r'^(?P<username>.*)(?P<tag>\n[A-Z0-9]+\n)? — (?P<time>\d{1,2}:\d{2}(?: [AP]M)?)'+
	WEEKDAYS+
	', '+MONTHS+r' (?P<day>\d{1,2}), (?P<year>\d{4}) (?P=time)$'
)

cymru_style_username_short_line_re=re.compile(
	r'^\[(?P<time>\d{2}:\d{2}(?: [AP]M)?)\]'+
	WEEKDAYS+
	r', (?P<day>\d{1,2}) '+MONTHS+r' (?P<year>\d{4}) at (?P=time)$'
)

cymru_style_username_full_line_re=re.compile(
	r'^(?P<username>.*)(?P<tag>\n[A-Z0-9]+\n)? — (?P<time>\d{2}:\d{2}(?: [AP]M)?)'+
	WEEKDAYS+
	r', (?P<day>\d{1,2}) '+MONTHS+r' (?P<year>\d{4}) at (?P=time)$'
)

USERNAME_LINE_REGEXES=[
	alice_style_username_full_line_re,
	alice_style_username_short_line_re,
	cymru_style_username_full_line_re,
	cymru_style_username_short_line_re,

]

ENDING_BUTTONS=[
	['Add Reaction','Edit','Forward','More'],
	['Add Reaction','Reply','Forward','More']
]
SIDE_TO_ANGLE_BRACKET={
	'later-left':'<',
	'left':'<',
	'right':'>',
}
SIDE_TO_ANGLE_BRACKET_REPLIES={
	'later-left':'>',
	'left':'>',
	'right':'<',
}
newline_re=re.compile(r'[\r\n]')

def parse_date(groups):
	return groups['time'],groups['year'],groups['month'],groups['day']

class Bucket:
	def __init__(self,user=None,dateparts=None):
		self.user=user
		self.dateparts=dateparts
		self.lines=[]
		self.parent = None
	
	def set_user(self,user):
		self.user = user
	
	def set_date(self, dateparts):
		self.dateparts = dateparts
	
	def add(self,line):
		line = line.rstrip()
		if line:
			self.lines.append(line)

	def is_reply(self, next_name):
		if len(self.lines)>2:
			#for a reply, the second to last line will start with an @
			#OR it'll be the same username as the user who is replying
			#So we have to check both
			return self.lines[-2].startswith('@') or self.lines[-2] == next_name
		return False

	def strip_reply(self):
		author, message = self.lines[-2:]
		self.lines=self.lines[:-2]
		return author.lstrip('@'), message

	def set_parent(self,parent):
		self.parent = parent

	def clean(self):
		lines=self.lines
		if lines[-1]=='NEW':
			lines=lines[:-1]
		if lines[-4:] in ENDING_BUTTONS:
			lines=lines[:-4]
		while lines[-1]=='Click to react' and lines[-2].startswith(':'):
			lines=lines[:-2]
		self.lines=lines

	def text(self):
		return self.lines[1]

	def __len__(self):
		return len(self.lines)
	def __repr__(self):
		return f'<Bucket [{self.user if self.user else '???'}] @{self.dateparts}>'

class BucketAccumulator:
	def __init__(self):
		self.buckets=[]
		self.last_bucket = Bucket()
	
	def add_line(self, line):
		self.check_for_new_bucket(line)
		self.last_bucket.add(line)
	
	def check_for_new_bucket(self,line):
		for regex in USERNAME_LINE_REGEXES:
			m=regex.search(line)
			if m:
				groups=m.groupdict()
				# If username is missing, use the last username
				# as this is a second-third-etc message in a row
				# from the same user
				username = groups.get('username',self.last_bucket.user)
				self.new_bucket(username,parse_date(groups))
				return True

	def new_bucket(self,user,dateparts):
		parent = None
		if self.last_bucket:
			if self.last_bucket.is_reply(user):
				parent = self.last_bucket.strip_reply()
			self.buckets.append(self.last_bucket)
		bucket = self.last_bucket=Bucket(user,dateparts)
		if parent is not None:
			bucket.set_parent(parent)

	def finalize_buckets(self):
		self.new_bucket(None,None)
		for bucket in self.buckets:
			bucket.clean()

	def add_possible_app_line(self, lines):
		combined = ''.join(lines)
		saved_last_bucket = self.last_bucket

		if self.check_for_new_bucket(combined):
			self.last_bucket.parent = None
			self.add_line(newline_re.sub(' ',combined))
		else:
			self.add_line(lines[-1])

def parse_input_to_buckets(lines):
	buckets=BucketAccumulator()
	for i,line in enumerate(lines):
		line=line.rstrip('\r\n')
		if line.startswith(' — '):
			buckets.add_possible_app_line(lines[i-2:i+1])
		else:
			buckets.add_line(line)

	buckets.finalize_buckets()
	return buckets.buckets

def debug_buckets(buckets):
	for bucket in buckets:
		print(f'{bucket}  LINES: {len(bucket)}')
		if bucket.parent is not None:
			for line in bucket.parent:
				print(f'\t + {line}')
		for line in bucket.lines:
			print(f'\t * {line}')

def get_speakers(buckets):
	speakers=set()
	for bucket in buckets:
		speakers.add(bucket.user)
		# specifically handle replied user
		# in case our log snippet includes a reply to 
		# someone who doesn't talk in the snippet
		if bucket.parent:
			speakers.add(bucket.parent[0])
	return speakers

def assign_sides(speakers, right_side=None):
	# the goal here is to be smart about who is picked for the right user
	sides={}

	available_sides=['later-left','left','right']
	if right_side in speakers:
		sides[right_side] = 'right'
		available_sides=['later-left','left']

	for speaker in speakers:
		if speaker not in sides:
			side=available_sides.pop()
			if not available_sides:
				available_sides=['later-left']
			sides[speaker]=side
	return sides

def parse_buckets_to_markdown(buckets, right_side=None):
	out=['```dialogue']
	speakers = get_speakers(buckets)
	last_left = None
	sides=assign_sides(speakers, right_side)
	for speaker,side in sides.items():
		if side in ('left','right'):
			out.append(f'{side}: {speaker}')
			if side=='left':
				last_left = speaker
	for bucket in buckets:
		user=bucket.user
		side=sides[user]
		if side in ('left','later-left') and user != last_left:
			last_left = user
			out.append(f'l:{user}')
		if bucket.parent: # despite the name, these are replies
			other_user, text = bucket.parent
			out.append(f'{SIDE_TO_ANGLE_BRACKET[sides[user]]}{SIDE_TO_ANGLE_BRACKET_REPLIES[sides[other_user]]} {text}')

		out.append(f'{SIDE_TO_ANGLE_BRACKET[sides[user]]} {bucket.text()}')

	out.append('```')
	return '\n'.join(out)

if __name__=='__main__':
	parser = argparse.ArgumentParser(description='Parse text copied out of Discord')
	parser.add_argument('filename')
	parser.add_argument('-r','--right',default=DEFAULT_RIGHT_USER,
		help="""If this user shows up in the log, make them the right-sided user
(Defaults to \'%(default)s\')""")
	parser.add_argument('-v','--verbose',action='store_true',
		help='Dump the message "buckets" before formatting them')
	parser.add_argument('-o','--output',metavar='FILE',help=
		'Output to FILE instead of printing to console')
	args = parser.parse_args()


	with open(args.filename,'r',encoding='utf-8') as f:
		lines=f.readlines()
		buckets=parse_input_to_buckets(lines)
		if args.verbose:
			debug_buckets(buckets)
		md=parse_buckets_to_markdown(buckets, args.right)
		if args.output:
			with open(args.output,'w',encoding='utf-8') as f:
				print(md, file=f)
		else:
			print(md)
