#!/usr/bin/python

""" TBill
A simple, hacky parser for Telstra bill files supplied to corporate/large clients.
Focused on outputting mobile data usage, but may be gradually expanded as needs require.

Creator: James Hodgkinson <yaleman at ricetek dot net>
"""

#import sys
import re,os
from Tkinter import *
import tkMessageBox
import tkFileDialog
import tkFont

class MyService( object ):
	def __init__(self, serviceid ):
		self.serviceid = serviceid
		self.header = ""
		self.datalines = []
		self.ignoredlines = []
		self.total = ""
		self.servicetype = ""
		self.planlines = []
		self.errors = []
		self.mobiledata = []
		self.mobile_data_total = 0.0
		self.mobile_data_ynv = "N"
		self.idd = []
		self.idd_total = ""
		self.ndd_total = 0.0
		self.user = ""
	def __eq__( self, otherserviceid ):
		if self.serviceid == otherserviceid:
			return True
		return False
	def __lt__( self, otherserviceid ):
		if self.serviceid < otherserviceid:
			return True
		return False
	def ismobiledata( self ):
		""" if there's lines in the mobiledata variable, it means there was usage """
		if len( self.mobiledata ) > 0:
			return True
		return False
	def isiddusage( self ):
		if len( self.idd ) > 0:
			return True
		return False
	
	#def __str__( self ):
	#	return self.serviceid
	#def __repr__( self ):
	#	return self.serviceid
	def set_header( self, string ):
		""" sets the header string for the service """
		self.header = string
	def set_servicetype(self, string):
		""" sets the service type for the service, expects a string """
		self.servicetype = string


class BillFile():
	def __init__( self, filename ):
		self.filename = filename
		self.fh = open( filename, "U" )
		self.services = []
	
		self.ignoredlines = [ "2S  D", "2S  H", "2S02D", "2D  H", "2S10D" ]
		self.lineparser = re.compile( "(?P<linetype>[A-Z]{6})(?P<account_name>[A-Z\s\.\-]{30})(?P<account_number>[0-9]{10})([\s]{8})(?P<filedate>[0-9]{6})(?P<service>[A-Z0-9\s\&]{10})[\s]{1,}(?P<line>.*)")
		self.header_parser = re.search( "HDR:(?P<filetype>[A-Z]{4})[\s]{1,}(?P<account_number>[0-9]{10})[\s]{1,}20(?P<filedate>[0-9]{6})(?P<remains>.*)", self.fh.readline().strip() )
		# parse_2S02V should find the plan's details in the service line
		self.parse_2S02V = re.compile( "[\s]{0,}(?P<plan>[A-Z0-9\$\-\/\s\.]{10,30})[\s]{0,}(?P<plandate>[0-9]{2} [A-Z]{3} TO [0-9]{2} [A-Z]{3})[\s]*(?P<exgst>[A-Z0-9\.\-]{4,})[\s]*([A-Z0-9\.\-]{4,})[\s]*(?P<gst>[A-Z0-9\.\-]{4,})[\s]*(?P<incgst>[A-Z0-9\.\-]{4,})" )
		# parse_plan_find_plan should find the plan within plan name
		self.parse_plan_find_plan = re.compile( "$([0-9]{1,})")
		# parse_service_type finds the service type, ignores the service number and should return the user
		self.parse_service_type = re.compile( "(?P<servicetype>[A-Z\s]*)[0-9]{8,}[\s]*USER: (?P<user>[A-Z0-9\.\s]*)")
		
		# parse 2S21V handles lines with voice calls
		self.parse_2S21V = re.compile( "[A-Z0-9\s]{46}[\s]*[0-9]*[\s]*[A-Z0-9]{5}[\s]*[A-Z0-9\s\/\(\)\-]{50}[\s]*([0-9]{0,} CALLS)[\s]*([0-9\,\.\-A-Z]*)" )

		#self.parse_2DTre = re.compile( "([A-Z0-9\s]{35,40}[\s]*[0-9]{10}[\s]*[0-9]*[\s]*2D  T[\s]*[\/\-\(\)\sA-Z0-9]*)\$([\,0-9\.\-]*)" )
		self.parse_2DTre = re.compile( "[\s]*([A-Z0-9\s\-\(\)\/\&]*)[\s]*\$([\,0-9\.\-]*)" )
		self.errors = []
		
		
		
		self.services, self.billdetails, self.linetypes = self.dofile( )

	def parse_2DT( self, line ):
	# parse 2S21V handles lines with voice calls
		stuff = self.parse_2DTre.search( line ).groups()
		foo = stuff[1].replace( ",", "" )
		if "GST FREE" in stuff[0]:
			foo = round( float( foo ) * 1.1, 2 )
		return foo
	def dofile( self ):
		linetypes = []
		data_services = []
		billdetails = ""
		for line in self.fh.read().split("\n"):
			if line.strip() == "" or line.strip() == "EOF":
				continue 
			res = self.lineparser.search( line )
			if not res:
				self.errors.append( "LINE-ERROR: %s" % line )
			else:
				#dline = res.groups()
				linetype = res.group( 'linetype' )
				serviceid = res.group( 'service' ).strip()
				line_details = res.group( 'line' )
				if linetype not in linetypes:
					linetypes.append( linetype )
				
				if serviceid not in data_services:
					data_services.append( MyService( serviceid ) )
					#print "Adding service: %s" % serviceid
				serviceindex = data_services.index( serviceid )
				this_service = data_services[ serviceindex ]
				if linetype == "RBMICA" and serviceid == "":
					billdetails += "%s\n" % line_details
				elif linetype == "RHMICA":
					header = line_details.strip()
					#this_service.set_header( header )
					pst = self.parse_service_type.search( header ) 
					if pst:
						this_service.user = pst.group( 'user' ).strip()
						this_service.servicetype = pst.group( 'servicetype' ).strip()
					else:
						this_service.servicetype = header.replace( this_service.serviceid, "" ).strip()
						this_service.user = header.replace( this_service.serviceid, "" ).replace( this_service.servicetype, "" ).replace( "USER:", "" ).strip()
					
				elif linetype == "RBMICA":
					ld = line_details.strip()
					line_subtype = ld[:5]
					ld = ld[5:]
					# should ignore some lines
					if line_subtype in self.ignoredlines:
						this_service.ignoredlines.append( [ line_subtype, ld.strip() ] )
						continue
					# grabs the line where they tell you the total service charges
					elif line_subtype == "2D  T":
						
						ynv = self.parse_2DT( ld )
						if ynv != "" and ynv != 0.00 and str( ynv ) != "0.00":
							this_service.mobile_data_ynv = str( ynv )
						elif this_service.ismobiledata():
							this_service.mobile_data_ynv = "Y"
						else:
							this_service.mobile_data_ynv = "N"
					elif line_subtype == "2S  T" and "TOTAL SERVICE CHARGES" in ld:
						this_service.total = ld.replace( "TOTAL SERVICE CHARGES", "" ).replace( "$", "" ).strip()
					# ignore lines which aren't the total service charges
					elif line_subtype == "2S  T":
						this_service.ignoredlines.append( [ line_subtype, ld.strip() ] )
					# national call costs, if they make phone calls
					elif line_subtype == "2S11V": 
						#print "National call"
						this_service.ndd_total = float( self.parse_2S21V.search( line ).groups()[1].replace( ",", "" ) )
					# idd voice charges
					elif line_subtype == "2S21V":
						this_service.idd_total = self.parse_2S21V.search( line ).groups()[1].replace( ",", "" )
					# these lines should show charges and stuff
					elif line_subtype == "2S02V":
						# this is the plan?
						plandetails = self.parse_2S02V.search( ld )
						if plandetails:
							plan_date = plandetails.group( 'plandate' ).strip()
							plan_name = plandetails.group( 'plan' ).strip()
							plan_incgst = plandetails.group( 'incgst' ).strip()
							if plan_incgst.endswith( "CR" ):
								plan_incgst = "-%s" % plan_incgst[:-2]
							plan_exgst = plandetails.group( 'exgst' ).strip()
							if plan_exgst.endswith( "CR" ):
								plan_exgst = "-%s" % plan_exgst[:-2]
							planvalue = self.parse_plan_find_plan.search( plan_name )
							if planvalue:
								plan_guess = int( planvalue.groups()[0] )
							else:
								plan_guess = None
							this_service.planlines.append( { 'date':plan_date, 'name':plan_name, 'incgst':plan_incgst, 'exgst':plan_exgst,'guess':plan_guess})
						else:
							this_service.errors.append( "Unable to parse 2S02V: %s" % ld )
					elif line_subtype == "2D10D" or line_subtype == "2S10V": # data
						this_service.mobiledata.append( ld.strip() )

					elif line_subtype == "2D21D": # voice calls/international calls
						this_service.idd.append( ld.strip() )
					else:
						this_service.errors.append( "Dataline: %s" % line_details.strip() )
		return data_services, billdetails, linetypes
	
	def dumperrors( self ):
		""" returns a string dump of the error lines to be dumped to a logfile """
		lines = ""
		for service in self.services:
			for error in service.errors:
				lines += "%s,%s\n" % (service.serviceid, error )
		#if lines == "":
		#	return "No Errors"
		self.dumperrors = lines
		return self.dumperrors	
	def dumpignored( self ):
		""" this returns a string dump of the ignored lines, so you can dump it to a logfile """
		lines = ""
		for service in self.services:
			for linetype, line in service.ignoredlines:
				lines += "%s: %s %s\n" % ( service.serviceid, linetype, line )
		return lines 	


	def printservice( self, this_service ):
		printval = "Service type: %s" % this_service.servicetype
		printval += "\nService ID: %s" % this_service.serviceid
		printval += "\nService total cost: %s" % this_service.total
		printval += "\nPlan lines:"
		for plan in this_service.planlines:
			printval += "\n%s" % str( plan )
		printval += "\n#Data lines: " 
		for dataline in this_service.datalines:
			printval += "\n%s" % dataline
		printval += "\n#Ignored lines"
		for ignoredline in this_service.ignoredlines:
			printval += "\n%s" % ignoredline
		printval += "\n#Errors:"
		for error in this_service.errors:
			printval += "\n%s" % str( error )
		return printval
	def csvit( self ): 
		lines = '"Service","Description","Plan Inc","Plan Ext","NULL","NULL","NULL","User","Cost"\n'
		for service in self.services:
			lines += self.serviceline( service )
		return lines
	
	def serviceline( self, ts ):
		retval = ""
		total_incgst = 0.00
		total_exgst = 0.00
		
		for line in ts.planlines:
			# there might be multiple plan lines, have to add 'em up
			if not line['guess']:
				line['guess'] = " "
			#retval += ",".join(  [ "\"+ts.serviceid+"\"", "\""+ts.servicetype+"\"", line['incgst'], line['exgst'], line['guess'] ] )+","
			#retval += ",".join( [ "\""+line['name']+"\"", "\""+line['date']+"\"","\""+ts.user+"\"" ] )+"\n" 
			total_incgst += float( line['incgst'] )
			total_exgst += float( line['exgst'] )
		data_idd = self.tftoyn( ts.isiddusage() )
		if data_idd == "Y" and ts.idd_total != 0.0:
			data_idd = ts.idd_total
			if ts.mobile_data_ynv == "N" or ts.mobile_data_ynv == "Y":
				ts.mobile_data_ynv = ts.idd_total
			else:
			#elif float( ts.mobile_data_ynv ) != 0.0:
				ts.mobile_data_ynv += str( float( ts.mobile_data_ynv ) + ts.idd_total )
		
		if ts.ndd_total != 0.0:
			if ts.mobile_data_ynv == "N" or ts.mobile_data_ynv == "Y":
				ts.mobile_data_ynv = ts.ndd_total
			else:
				ts.mobile_data_ynv += str( float( ts.ndd_total ) + ts.mobile_data_ynv )
		#, data_idd	
		retval += '="%s","CALCULATED TOTAL",%s,%s," "," "," ","%s",%s\n' % ( ts.serviceid, total_incgst, total_exgst, ts.user, ts.mobile_data_ynv )
		return retval
	def tftoyn( self, value ):
		isdata = { 'True':'Y', 'False':'N' }
		return isdata[ str( value ) ]
			
	def writefiles( self ):
		sourcefile = self.filename.replace( ".DAT", "" )
		string_to_file( "\n".join( self.errors ), sourcefile+"-errors.txt" )
		string_to_file( self.dumperrors(  ), sourcefile+"-dumperrors.txt" )
		string_to_file( self.csvit(  ), sourcefile+".csv" )
		string_to_file( self.dumpignored( ), sourcefile+"-ignored.txt" )


def string_to_file( string, filename ):
	fh = open( filename, "w" )
	fh.write( string )

def totcount( i ):
	x = "".join( i )
	return len( x )




class CNTParser():
	def __init__(self, directory ):
		self.directory = directory
		self.siteid = ""
		self.sitename = ""
		self.accounts = []
		
		self.linefinder = re.compile( "(?P<accname>[A-Z0-09\s]*),(?P<accnum>[0-9]*),([0-9A-Z]*),(?P<filedate>[0-9A-Z]*),(?P<filename>[A-Z0-9\.]*),(?P<billsystem>[A-Z0-9]*),\$[\s]*(?P<totinc>[0-9A-Z\.\-]*)[\s]*,\$[\s]*(?P<gst>[0-9A-Z\.\-]*)[\s]*,\$[\s]*(?P<adjustments>[0-9A-Z\.\-]*)[\s]*")
		
		for filename in os.listdir( directory ):
			if filename.startswith( "CNT" ) and filename.endswith( "CSV" ):
				self.filename = filename
				break
		self.processfile()
		
	def crdr( self, item ):
		if item.endswith( "CR" ):
			item = "-%s" % item[:-2]
		return item
	def processfile( self ):
		fh = open( self.filename, "U" )
		filecontents = fh.read().replace( "\r", "" )
		for line in filecontents.split( "\n" ):
			#print "'%s'" % line
			if line.startswith( "Site ID:" ):
				self.siteid = line.replace( "Site ID: ", "" ).strip()
			elif line.startswith( "Site Name:"):
				self.sitename = line.replace( "Site Name: ", "" ).strip()
			elif ".DAT" in line:
				#print line 
				res = self.linefinder.search( line )
				if res:
					accname,accnum,otherid,filedate,filename,billsystem,incgst,gst,adjust = res.groups()
					otherid = otherid #to shut eclipse up
					incgst = self.crdr( incgst )
					gst = self.crdr( gst )
					adjust = self.crdr( adjust )
					self.accounts.append( { 'account_name':accname, 'account_number':accnum, 'filedate':filedate, 'filename':filename,'billsystem':billsystem,'total_incgst':incgst,'total_gst':gst,'total_adjustments':adjust} )
		#print "Site ID: %s" % self.siteid
		#print "Site Name: %s" % self.sitename
		#print "\n".join( [ str( account ) for account in self.accounts ]  )



class Controller( Frame ):
	def __init__(self, parent ):
		""" starter code for the Controller class
		"""
		Frame.__init__( self, parent, width=80, height=50 )
		self._parent = parent
		self.ACC_FORMAT = "{0:<15}{1:<12}{2:<35}{3:>12}{4:>12}{5:>12}"
		self.parsedir = "./telstra/"
		self.cntfile = CNTParser( self.parsedir )
		#for account in self.cntfile.accounts:
		#	print account
			#bill = BillFile( account['filename'] )
			#bill.writefiles()
		self.createWidgets()
		self.bills = []

	def createWidgets( self ):
		

		self.font = tkFont.Font( family="Courier", size=12 )
		Label( text= self.ACC_FORMAT.format( "Filename", "Account #", "Account Name", "Total Inc.", "Gst Amount","Adjustments" ), font=self.font).pack()
		self.filebox = Listbox( width=100, font=self.font )
		#FRIENDS_FORMAT = "{0:<20}{1:<50}{2:<12}{3:<10}"
		#return FRIENDS_FORMAT.format( self.name, self.address, self.phone, sbirth )
		self.updatelist()
		self.filebox.pack( )
		Button( text='Process File', command=self.processfile ).pack()
		Button( text='Dump Readable File', command=self.dumpreadable ).pack()
		Button( text='Update List', command=self.updatelist ).pack()
		
	
	def updatelist( self ):
		self.filebox.delete( 0, END )
		#self.filebox.insert( END, self.ACC_FORMAT.format( "Filename", "Account #", "Account Name", "Total Inc.", "Gst Amount","Adjustments" ))
		for account in self.cntfile.accounts:
			stracc = self.ACC_FORMAT.format( account['filename'], account['account_number'], account['account_name'], account['total_incgst'], account['total_gst'], account['total_adjustments'] )
			self.filebox.insert( END, stracc )
			#self.filebox.insert( END, "%s %s" % ( account['account_number'], account['account_name'] ) )
	def getselection( self ):
		selection = self.filebox.curselection()
		if selection == ():
			tkMessageBox.showerror("Whoops!", "No line selected")
		else:
			fileselection = self.filebox.get( selection )
			return fileselection
	def getfilenamefromselection( self, selection ):
		return selection.split( " " )[0].strip()
	
	def dumpreadable( self ):
		filename = self.getfilenamefromselection( self.getselection() )
		fh = open( filename, "U" )
		newfile = "\r\n".join( [ line[60:] for line in fh.read().split( "\n" ) ] )
		fh.close()
		newfilename = filename.replace( ".", "-readable." )
		newfilename = newfilename.replace( 'DAT', 'txt' )
		fh = open( self.parsedir+'/'+newfilename,'w' )
		fh.write( newfile )
		fh.close
		self.filebox.insert( END, "Dumped readable file {0}".format( newfilename ) ) 
	
	def processfile( self ):
		filename = self.getfilenamefromselection( self.getselection() )
	
		self.filebox.insert( END, "Processing file: %s" % filename )
		billfile = BillFile( self.parsedir + "/" + filename )
		billfile.writefiles()
		self.bills.append( billfile )
		self.filebox.insert( END, "Completed processing file %s" % filename )
			

class TBillApp():
	def __init__(self, master=None):
		master.title("TBill")
		self.controller = Controller(master)

def main():
	root = Tk()
	app = TBillApp(root)
	root.mainloop()
	
if  __name__ == '__main__':
	main()
