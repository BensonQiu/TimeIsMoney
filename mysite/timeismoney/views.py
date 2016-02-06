import datetime

from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import render, redirect

from timeismoney.models import *

def parseDate(daterange):
	# Convert '02/06/2016 12:00 AM - 02/06/2016 11:59 PM'
	# to (2016-02-0600T00, 2016-02-06023T59)
	daterange = daterange.split('-')

	startDateMonth = daterange[0].strip().split()[0].split('/')[0]
	startDateDay = daterange[0].strip().split()[0].split('/')[1]
	startDateYear = daterange[0].strip().split()[0].split('/')[2]
	startTime = daterange[0].strip().split()[1]
	startAMPM = daterange[0].strip().split()[2]
	startHour = startTime.split(':')[0]
	startMinute = startTime.split(':')[1]
	if startHour == '12' and startAMPM == 'AM':
		startHour = '00'
	if startAMPM == 'PM':
		startHour = str(int(startHour)+12)
	if startHour != '00' and len(startHour) == 1:
		startHour = '0' + startHour

	endDateMonth = daterange[1].strip().split()[0].split('/')[0]
	endDateDay = daterange[1].strip().split()[0].split('/')[1]
	endDateYear = daterange[1].strip().split()[0].split('/')[2]
	endTime = daterange[1].strip().split()[1]
	endAMPM = daterange[1].strip().split()[2]
	endHour = endTime.split(':')[0]
	endMinute = endTime.split(':')[1]
	if endHour == '12' and endAMPM == 'AM':
		endHour = '00'
	if endAMPM == 'PM':
		endHour = str(int(endHour)+12)
	if endHour != '00' and len(endHour) == 1:
		endHour = '0' + endHour

	startDateTime = ("{startDateYear}-{startDateMonth}-{startDateDay}"
                     "{startHour}T{startMinute}"
		            ).format(
		            	startDateYear=startDateYear,
		            	startDateMonth=startDateMonth,
		            	startDateDay=startDateDay,
		            	startHour=startHour,
		            	startMinute=startMinute,
		            )

	endDateTime = ("{endDateYear}-{endDateMonth}-{endDateDay}"
                   "{endHour}T{endMinute}"
		          ).format(
		            	endDateYear=endDateYear,
		            	endDateMonth=endDateMonth,
		            	endDateDay=endDateDay,
		            	endHour=endHour,
		            	endMinute=endMinute,
		            )
	return (startDateTime, endDateTime)

@login_required
def attend(request, id):
	username = request.user.username
	meeting = Meeting.objects.filter(id=id)[0]
	meeting.pendingAttendees.remove(request.user)
	meeting.acceptedAttendees.add(request.user)
	meeting.save()

	return redirect(reverse('home'))

@login_required
def createMeeting(request):
	context = {}

	# if request.method == 'GET':
	# 	return render(request, 'timeismoney/createMeeting.html', context)

	# TODO: Create a form to validate input
	# form = request.POST
	form = request.GET

	(startDT, endDT) = parseDate(form['date'])

	newMeeting = Meeting(
		meetingName=form['meetingName'],
		startDT=startDT,
		endDT=endDT,
		location=form['address'],
		latitude=form['lat'],
		longitude=form['lng']
	)
	newMeeting.save()
	# Meeting creator is automatically attending
	newMeeting.acceptedAttendees.add(request.user)
	newMeeting.save()

	for attendee in form.getlist('attendees[]'):
		user = User.objects.filter(username=attendee)[0]
		newMeeting.pendingAttendees.add(user)
		newMeeting.save()

	return redirect(reverse('home'))

@login_required
def checkIn(request):
	context = {}

	if request.method == 'GET':
		return render(request, 'timeismoney/checkIn.html', context)

	context['userLat'] = request.POST['checkin-lat']
	context['userLng'] = request.POST['checkin-lng']
	context['meetings'] = Meeting.objects.all()

	return render(request, 'timeismoney/checkIn.html', context)

@login_required
def summary(request):
	context = {}

	if request.method == 'GET':
		return render(request, 'timeismoney/summary.html', context)
	context['meetings'] = Meeting.objects.all()
	return render(request, 'timeismoney/summary.html', context)

@login_required
def getData(request):
	meetings = list(Meeting.objects.all())
	meetings_response = [
		{
			'meetingName': meeting.meetingName,
			'startDT': meeting.startDT,
			'endDT': meeting.endDT,
			'location': meeting.location,
		}
		for meeting in meetings
		if not meeting.pendingAttendees.values()
		and request.user in meeting.acceptedAttendees.all()]

	context = {
		'success': True,
		'meetings': meetings_response,
		'testdata': 'bensonwashere',
	}
	return JsonResponse(context)

@login_required
def getUsernames(request):
	users = list(User.objects.all())
	# Get all usernames except the current user's username
	usernames = [user.username for user in users if user != request.user]

	context = {
		'success': True,
		'usernames': usernames,
		'testdata': 'bqiuwashere',
	}
	return JsonResponse(context)

@login_required
def home(request):
	meetings = Meeting.objects.all()
	acceptedMeetings = filter(
		lambda meeting: not meeting.pendingAttendees.values_list(), meetings
	)
	pendingMeetings = filter(
		lambda meeting: meeting.pendingAttendees.values_list(), meetings
	)
	context = {
		'acceptedMeetings': acceptedMeetings,
		'pendingMeetings': pendingMeetings,
		'first_name': request.user.first_name,
		'last_name': request.user.last_name,
	}

	return render(request, 'timeismoney/index.html', context)

@transaction.atomic
def register(request):

	# If this is a GET request, display the registration form.
	if request.method == 'GET':
		return render(request, 'timeismoney/register.html', {})

	# TODO: Create a form to validate input
	form = request.POST
	# TODO: Do form validation here.

	newUser = User.objects.create_user(
		username=form['username'],
		password=form['password1'],
		first_name=form['first_name'],
		last_name=form['last_name'],
		email=form['email'], # This is actually CapitalOne Account ID.
		                     # If this wasn't a hackathon we should probably
		                     # just extend User to add additional fields
	)

	return render(request, 'timeismoney/login.html', {})

def withinStart(startDT):
	startYear = int(startDT[0:4])
	startMonth = int(startDT[5].strip('0') + startDT[6])
	startDay = int(startDT[8].strip('0') + startDT[9])
	startHour = int(startDT[10].strip('0') + startDT[11])
	startMinute = int(startDT[13].strip('0') + startDT[14])

	gmt = pytz.timezone('GMT')
	eastern = pytz.timezone('US/Eastern')
	dategmt = gmt.localize(datetime.datetime.now() - timedelta(mins=30))
	currDT = dategmt.astimezone(eastern)
	currYear = currDT.year
	currMonth = currDT.month
	currDay = currDT.day
	currHour = currDT.time().hour
	currMinute = currDT.time().minute

	return currYear >= startYear and currMonth >= startMonth and currDay >= startDay and \
	       currHour >= startHour and currMinute >= startHour
