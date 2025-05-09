from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, logout, login as auth_login, logout as auth_logout, get_user_model
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import send_mail, EmailMessage
from django.core.validators import validate_email
from django.conf import settings
from django.db import transaction, IntegrityError
from django.http import JsonResponse, HttpResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.urls import reverse
from django.db.models import Q, F
from django.views import View
from django.utils.decorators import method_decorator
from django.core.serializers.json import DjangoJSONEncoder
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from home.models import Users, Moderator, Customers, Bus, Location, BusBooking, Payment, Notification, Agent, TravelReport, DriversInfo, AgentJob, TourPackage, MissingPerson, Police, Detected
from home.forms import BusForm, CustomerProfileForm
from home.utils import render_to_pdf
import logging
import stripe
import os
import re
import json

# Conditionally import pandas based on ML features flag
if getattr(settings, 'ENABLE_ML_FEATURES', False):
    import pandas as pd
else:
    # Create a dummy pandas module for compatibility
    class DummyPd:
        class DataFrame:
            def __init__(self, *args, **kwargs):
                self.data = {}
            
            def to_dict(self, *args, **kwargs):
                return {}
            
            @classmethod
            def from_dict(cls, *args, **kwargs):
                return cls()
            
            def to_csv(self, *args, **kwargs):
                pass
            
            @classmethod
            def read_csv(cls, *args, **kwargs):
                return cls()
    
    pd = DummyPd()

from datetime import date, datetime, timedelta
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from home.models import Bus, Agent, SafetyNotificationReport, Moderator
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import JsonResponse
from home.models import Agent, Moderator
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.http import JsonResponse
from django.db import IntegrityError
from django.views.decorators.http import require_GET
from home.models import Bus
from home.models import Police
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

import logging
logger = logging.getLogger(__name__)

class ChatbotResponse:
    def __init__(self):
        # Simple rule-based chatbot without Generative AI
        logger.info("Initializing simple rule-based chatbot")
        # Initialize responses
        self.responses = {
            "booking": {
                "keywords": ["book", "reserve", "schedule", "ticket"],
                "response": "To make a booking, you can use our online booking system on the homepage. "
                           "We'll need your travel dates, destination, and number of travelers. "
                           "Would you like me to guide you through the process?"
            },
            "cancellation": {
                "keywords": ["cancel", "refund", "terminate", "void"],
                "response": "You can cancel your booking through 'My Trips' section. "
                           "Refunds are typically processed within 5-7 business days. "
                           "Would you like to know about our cancellation policy?"
            },
            "rescheduling": {
                "keywords": ["reschedule", "change date", "modify", "change booking"],
                "response": "To reschedule your trip, go to 'My Trips' and select the booking you want to modify. "
                           "Changes made at least 48 hours before departure usually don't incur extra charges."
            },
            "payment": {
                "keywords": ["payment", "pay", "cost", "price", "fee"],
                "response": "We accept various payment methods including credit/debit cards and UPI. "
                           "All payments are processed securely through Stripe. "
                           "Would you like to know more about our payment options?"
            },
            "safety": {
                "keywords": ["safe", "security", "covid", "health", "protection"],
                "response": "Your safety is our top priority! We follow all health and safety guidelines, "
                           "and our vehicles are regularly sanitized. We also have a 24/7 alert system "
                           "for any safety-related updates."
            },
            "contact": {
                "keywords": ["contact", "support", "help", "phone", "email"],
                "response": "Our customer support team is available 24/7. You can reach us at: "
                           "Email: support@logu.com "
                           "Phone: +1-234-567-8900"
            },
            "missing": {
                "keywords": ["missing", "lost", "find", "person", "locate", "face", "recognition"],
                "response": "Our face recognition system can help identify missing persons. Please report any missing "
                           "person cases to the nearest police station or use our 'Report Missing Person' feature."
            }
        }

    def get_response(self, message):
        """Get response using keyword matching"""
        logger.info(f"Processing message: {message}")
        message = message.lower()
        for intent, data in self.responses.items():
            if any(keyword in message for keyword in data["keywords"]):
                logger.info(f"Found matching intent: {intent}")
                return {
                    "status": "success",
                    "reply": data["response"],
                    "intent": intent
                }
        
        logger.info("No matching intent found, using default response")
        return {
            "status": "success",
            "reply": "I'm here to help with your travel needs! You can ask me about bookings, cancellations, payments, or our safety measures. What would you like to know?",
            "intent": "default"
        }

# Initialize chatbot globally
chatbot = ChatbotResponse()

@csrf_exempt
def chat_message(request):
    """Handle chat messages and return appropriate responses"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '').strip()
            
            if not user_message:
                return JsonResponse({
                    "status": "error",
                    "message": "Please provide a message"
                })
            
            # Get response from chatbot
            response = chatbot.get_response(user_message)
            return JsonResponse(response)
            
        except json.JSONDecodeError:
            return JsonResponse({
                "status": "error",
                "message": "Invalid JSON data"
            })
        except Exception as e:
            return JsonResponse({
                "status": "error",
                "message": str(e)
            })
    
    return JsonResponse({
        "status": "error",
        "message": "Only POST requests are allowed"
    })



# Set up logging
logger = logging.getLogger(__name__)

user = get_user_model()

@transaction.atomic
def deactivate_customer(request, customer_id):
    if request.method == 'POST':
        customer = get_object_or_404(Customers, customer_id=customer_id)
        user = customer.user
        
        # Delete the customer and associated user
        customer.delete()
        user.delete()
        
        messages.success(request, f"Customer {customer.first_name} {customer.last_name} has been deactivated and removed from the system.")
    
    return redirect('customer_details')

def logout_required(view_func):
    def wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('index')  # Redirect to welcome page if user is authenticated
        return view_func(request, *args, **kwargs)
    return wrapped_view


def index(request):
    return render(request, 'index.html')



def profile(request):
    try:
        customer = Customers.objects.get(email=request.user.email)
    except Customers.DoesNotExist:
        customer = None
    return render(request, 'profile.html', {'customer': customer})

import logging

logger = logging.getLogger(__name__)

@login_required
def welcomePage(request):
    if request.user.is_authenticated:
        try:
            customer = Customers.objects.get(user=request.user)
        except Customers.DoesNotExist:
            logger.warning(f"Customer not found for user {request.user.username}")
            customer = None
        context = {'customer': customer}
    else:
        context = {}
    return render(request, 'welcome.html', context)


@login_required
def get_safety_alerts(request):
    if request.user.is_authenticated:
        unread_alerts = Notification.objects.filter(
            user=request.user,
            is_read=False,
            message__startswith="Safety Alert:"
        ).order_by('-created_at')

        if unread_alerts.exists():
            alerts = [{"message": alert.message} for alert in unread_alerts]
            unread_alerts.update(is_read=True)
            return JsonResponse({
                'has_alerts': True,
                'alerts': alerts
            })
    
    return JsonResponse({'has_alerts': False})


# @logout_required
@csrf_protect
def loginn(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Authenticate the user
        user = authenticate(request, username=email, password=password)
        print(f'Authentication result: {user}')

        if user is not None:
            print(f'User authenticated: {user.email}')

            # Check if the user's login is disabled
            if user.loginstatus == 'disabled':
                return render(request, 'login.html', {'error': 'Your account has been disabled. Please contact the administrator.'})

            auth_login(request, user)
            user.set_status_active()

            # Check user type and redirect accordingly
            if user.user_type == 'police':
                try:
                    police = Police.objects.get(user=user)  # Use the user object, not email
                    return redirect('policehome')
                except Police.DoesNotExist:
                    messages.error(request, "Police profile not found")
                    return redirect('login')
            elif user.user_type == 'agent':
                agent = Agent.objects.get(user=user)  # Similarly use user object here
                if agent.status == 'Approved':
                    return redirect('agent_welcome')
                else:
                    return render(request, 'pending_registration.html', {'message': 'Your registration is pending approval.'})

            # Check if the user is a moderator
            moderator = Moderator.objects.filter(email=email).first()  # This line might also need to be changed to use user object
            
            # Check if the user is an agent
            agent = Agent.objects.filter(email=email).first()

            if moderator:
                print(f'Moderator status: {moderator.status}')

                if moderator.status == 'Pending':
                    return render(request, 'pending_registration.html', {'message': 'Your registration request is pending. After the admin accepts it, you can log in to the system.'})
                elif moderator.status == 'Rejected':
                    return render(request, 'pending_registration.html', {'message': 'Your registration request was rejected. Please contact support for more details.'})
                elif moderator.status == 'Approved':
                    if user.loginstatus == 'enabled':
                        user.set_status_active()
                        auth_login(request, user)
                        return redirect('mod_home')
                    else:
                        return render(request, 'login.html', {'error': 'Your account has been disabled. Please contact the administrator.'})

            elif agent:
                print(f'Agent status: {agent.status}')

                if agent.status == 'Pending':
                    return render(request, 'pending_registration.html', {'message': 'Your registration request is pending. After the moderator accepts it, you can log in to the system.'})
                elif agent.status == 'Rejected':
                    return render(request, 'pending_registration.html', {'message': 'Your registration request was rejected. Please contact support for more details.'})
                elif agent.status == 'Approved':
                    user.set_status_active()
                    auth_login(request, user)
                    return redirect('agent_welcome')  # Redirect to agent home

            else:
                # Log the user in if not a moderator or agent
                user.set_status_active()
                auth_login(request, user)
                if user.email == 'admin@gmail.com':
                    print('Redirecting to admin panel.')
                    return redirect('admin1')
                else:
                    print('Redirecting to welcome page.')
                    return redirect('welcome')  # Default redirection for other user types

        else:
            print('Invalid email or password.')
            return render(request, 'login.html', {'error': 'Invalid Email or Password'})

    print('GET request received, rendering login page.')
    return render(request, 'login.html')


def signout(request):
    if request.user.is_authenticated:
        request.user.set_status_inactive()
    auth_logout(request)
    response = redirect('index')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response



def pending_registration(request):
    return render(request, 'pending_registration.html', {'message': 'Your registration request is pending. After the admin accepts it, you can log in to the system.'})



@login_required
def mod_req_details(request):
    pending_moderators = Moderator.objects.filter(status='Pending')

    if request.method == 'POST':
        moderator_id = request.POST.get('moderator_id')
        action = request.POST.get('action')
        moderator_email = request.POST.get('moderator_email')

        if moderator_id:
            moderator = get_object_or_404(Moderator, moderator_id=moderator_id)
            if action == 'accept':
                moderator.status = 'Approved'
                moderator.save()
                messages.success(request, f'Moderator {moderator.first_name} {moderator.last_name} approved successfully.')

                # Send email
                subject = 'Your moderator request has been accepted'
                message = 'Congratulations! You can now log in to our system.'
                from_email = settings.DEFAULT_FROM_EMAIL
                recipient_list = [moderator_email]

                try:
                    send_mail(subject, message, from_email, recipient_list)
                    messages.success(request, f'Acceptance email sent to {moderator_email}')
                except Exception as e:
                    messages.error(request, f'Failed to send email: {str(e)}')

            elif action == 'reject':
                moderator.status = 'Rejected'
                moderator.save()
                messages.error(request, f'Moderator {moderator.first_name} {moderator.last_name} rejected.')

            return redirect('mod_req_details')

    return render(request, 'mod_req_details.html', {'pending_moderators': pending_moderators})




def signup(request):
    if request.method == "POST":
        logger.info(f"Received POST data: {request.POST}")
        fname = request.POST.get('f_name')
        lname = request.POST.get('l_name')
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        city = request.POST.get('city')
        district = request.POST.get('district')
        postal_code = request.POST.get('postal_code')

        errors = []

        if not all([fname, lname, address, phone, email, password, password_confirm, city, district, postal_code]):
            errors.append("All fields are required.")

        try:
            validate_email(email)
        except ValidationError:
            errors.append("Invalid email format.")

        if len(password) < 8:
            errors.append("Password must be at least 8 characters long.")

        if password != password_confirm:
            errors.append("Passwords do not match.")

        if Customers.objects.filter(email=email).exists():
            errors.append("This email is already registered.")

        if errors:
            return render(request, 'signup.html', {'errors': errors})

        try:
            user = Users.objects.create_user(
                username=email, 
                email=email, 
                first_name=fname, 
                last_name=lname,
                password=password, 
                user_type='customers'
            )

            # Create customer profile in Customers table
            customer = Customers(
                user=user, 
                email=email, 
                first_name=fname, 
                last_name=lname, 
                address=address, 
                phone=phone,
                city=city,
                district=district,
                postal_code=postal_code
            )
            customer.save()

            messages.success(request, 'User created successfully')
            return redirect('login')
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
    
    else:
        logger.info("Received GET request for signup page")
    return render(request, 'signup.html')



@require_POST
@csrf_protect
def check_email(request):
    email = request.POST.get('email')
    exists = (
        Customers.objects.filter(email=email).exists() or 
        Moderator.objects.filter(email=email).exists() or
        Agent.objects.filter(email=email).exists()
    )
    return JsonResponse({'exists': exists})








@login_required
def booking(request):
    return render(request, 'booking.html', )



 

from django.db.models import Sum
from datetime import datetime, timedelta
from decimal import Decimal

@login_required
def admin1(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Total Users
    total_users = Customers.objects.count() + Moderator.objects.count() + Agent.objects.count()
    
    # Total Revenue
    total_revenue = Payment.objects.filter(status='completed').aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    # Total Buses
    total_buses = Bus.objects.count()
    
    # Total Feedback
    total_feedback = Feedback.objects.count()
    
    # Get individual counts
    customer_count = Customers.objects.count()
    moderator_count = Moderator.objects.count()
    agents_count = Agent.objects.count()
    
    # Calculate revenue data for the chart
    current_month = datetime.now().month
    revenue_data = [float(total_revenue * Decimal(1 + 0.1 * i)) for i in range(6)]
    months = [(datetime.now() - timedelta(days=30*i)).strftime('%b') for i in range(5, -1, -1)]
    
    # TBSC Statistics data
    from home.models import MissingPerson, Police, Users, Detected
    from django.db.models import Count, Avg, F, ExpressionWrapper, fields, Q
    from django.utils import timezone
    import json
    
    # Active Cases - Missing persons that are not finished
    active_cases_count = MissingPerson.objects.filter(is_finished=False).count()
    
    # Police Stations count
    police_station_count = Police.objects.count()
    
    # Total Users (including police and regular users)
    user_count = Users.objects.count()
    
    # Surveillance Alerts - Count of detections
    surveillance_alerts = Detected.objects.count()
    
    # Enhanced Case Analytics
    cases_by_status = {
        'open': MissingPerson.objects.filter(status='open').count(),
        'investigating': MissingPerson.objects.filter(status='investigating').count(),
        'closed': MissingPerson.objects.filter(status='closed').count()
    }
    
    # Calculate case resolution rate
    total_cases = MissingPerson.objects.count()
    resolved_cases = MissingPerson.objects.filter(is_finished=True).count()
    case_resolution_rate = (resolved_cases / total_cases * 100) if total_cases > 0 else 0
    
    # Calculate average time to resolve (for closed cases with date_reported)
    # Using a 30-day default for cases without proper timestamps
    thirty_days = timezone.timedelta(days=30)
    resolved_cases_with_dates = MissingPerson.objects.filter(
        is_finished=True, 
        date_reported__isnull=False
    )
    
    if resolved_cases_with_dates.exists():
        avg_resolution_time = resolved_cases_with_dates.annotate(
            resolution_days=ExpressionWrapper(
                F('date_reported') - timezone.now(),
                output_field=fields.DurationField()
            )
        ).aggregate(avg=Avg('resolution_days'))['avg']
        avg_resolution_days = abs(avg_resolution_time.days) if avg_resolution_time else 30
    else:
        avg_resolution_days = 30
    
    # Geographic distribution - Top 5 locations with most cases
    geographic_distribution = MissingPerson.objects.values('location')\
        .annotate(count=Count('id'))\
        .order_by('-count')[:5]
    
    geo_labels = [item['location'] or 'Unknown' for item in geographic_distribution]
    geo_data = [item['count'] for item in geographic_distribution]
    
    # Surveillance Performance Metrics
    # For demonstration, we'll create sample data based on actual counts
    # In a real implementation, this would come from actual measurements
    detection_methods = {
        'HOG': {'count': Detected.objects.count() * 0.6, 'accuracy': 70},
        'CNN': {'count': Detected.objects.count() * 0.3, 'accuracy': 88},
        'Cascaded': {'count': Detected.objects.count() * 0.1, 'accuracy': 75}
    }
    
    # Detection trends (simulated data for demonstration)
    # In a real implementation, this would use actual timestamps
    detection_trends = []
    base_count = Detected.objects.count() // 6 if Detected.objects.count() > 0 else 5
    for i in range(6):
        # Create some variation in the data
        variation = (i * 0.2) + 0.8
        detection_trends.append(round(base_count * variation))
    
    # User Engagement Metrics
    # Active users by type
    police_users = Users.objects.filter(user_type='police').count()
    regular_users = Users.objects.filter(user_type='user').count()
    
    # Most active police stations - Top 5
    active_police_stations = Police.objects.annotate(
        case_count=Count('investigating_cases')
    ).order_by('-case_count')[:5]
    
    station_labels = [station.policestation or 'Unnamed Station' for station in active_police_stations]
    station_data = [station.case_count for station in active_police_stations]
    
    context = {
        'total_users': total_users,
        'total_revenue': float(total_revenue),
        'total_buses': total_buses,
        'total_feedback': total_feedback,
        'customer_count': customer_count,
        'moderator_count': moderator_count,
        'agents_count': agents_count,
        'revenue_data': revenue_data,
        'revenue_months': months,
        # TBSC Statistics data
        'active_cases_count': active_cases_count,
        'police_station_count': police_station_count,
        'user_count': user_count,
        'surveillance_alerts': surveillance_alerts,
        
        # Enhanced Case Analytics
        'cases_by_status': cases_by_status,
        'case_resolution_rate': round(case_resolution_rate, 1),
        'avg_resolution_days': avg_resolution_days,
        'geo_labels': json.dumps(geo_labels),
        'geo_data': json.dumps(geo_data),
        
        # Surveillance Performance Metrics
        'detection_methods': detection_methods,
        'detection_trends': json.dumps(detection_trends),
        'detection_months': json.dumps(months),  # Reuse the same months as revenue
        
        # User Engagement Metrics
        'police_users': police_users,
        'regular_users': regular_users,
        'station_labels': json.dumps(station_labels),
        'station_data': json.dumps(station_data),
    }
    
    return render(request, 'admin1.html', context)



def mod_reg(request):
    return render(request, 'mod_reg.html')



@login_required
def mod_sch(request):
    try:
        moderator = Moderator.objects.get(user=request.user)
        locations = Location.objects.all().order_by('source', 'destination').values('source', 'source_code', 'destination', 'destination_code', 'stops')
        locations_json = json.dumps(list(locations), cls=DjangoJSONEncoder)
        
        if request.method == 'POST':
            form = BusForm(request.POST, request.FILES)
            if form.is_valid():
                bus = form.save(commit=False)
                bus.moderator_id = moderator
                bus.save()
                messages.success(request, 'Bus added successfully.')
                return redirect('mod_home')
        else:
            form = BusForm()
        
        context = {
            'moderator': moderator,
            'locations': locations_json,
            'form': form,
        }
        return render(request, 'mod_sch.html', context)
    except Moderator.DoesNotExist:
        return redirect('index')

def get_stops(request):
    departure = request.GET.get('departure')
    destination = request.GET.get('destination')
    
    try:
        location = Location.objects.get(source=departure, destination=destination)
        stops = location.get_stops_list()
        return JsonResponse({'success': True, 'stops': stops})
    except Location.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'No routes currently available for the selected locations. Please select other locations.'})


def signup_moderator(request):
    if request.method == "POST":
        fname = request.POST['f_name']
        lname = request.POST['l_name']
        mobile = request.POST['mobile']
        email = request.POST['email']
        password = request.POST['password']
        password_confirm = request.POST.get('password_confirm', '')
        gst = request.POST.get('gst', '')
        pan = request.POST.get('pan', '')
        pan_name = request.POST.get('pan_name', '')
        aadhar = request.POST.get('aadhar', '')
        company = request.POST.get('company', '')
        city = request.POST.get('city', '')
        
        errors = {}

        if password != password_confirm:
            errors['password'] = 'Passwords do not match'
        
        if Moderator.objects.filter(email=email).exists():
            errors['email'] = 'This email is already registered'

        if errors:
            return render(request, 'mod_reg.html', {'errors': errors})
        
        try:
            with transaction.atomic():
                # Create login entry in Users table
                user = Users.objects.create_user(
                    username=email, 
                    email=email, 
                    password=password, 
                    user_type='moderator'
                )
                
                # Create moderator profile in Moderator table
                moderator = Moderator(
                    user=user,
                    first_name=fname,
                    last_name=lname,
                    mobile=mobile,
                    email=email,
                    password=make_password(password),
                    gst=gst,
                    pan=pan,
                    pan_name=pan_name,
                    aadhar=aadhar,
                    company=company,
                    city=city,
                    user_type='moderator'
                )
                
                # Handle the CV file
                if 'cv_file' in request.FILES:
                    moderator.cv_file = request.FILES['cv_file']
                
                # Save the moderator profile
                moderator.save()
            
            messages.success(request, 'Moderator created successfully')
            return redirect('login')
        except Exception as e:
            errors['general'] = f"Error: {str(e)}"
            return render(request, 'mod_reg.html', {'errors': errors})
    return render(request, 'mod_reg.html')

@login_required
def mod_profile(request):
    try:
        moderator = Moderator.objects.get(user=request.user)
        
        if request.method == "POST":
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            mobile = request.POST.get('mobile')
            email = request.POST.get('email')
            company = request.POST.get('company')
            city = request.POST.get('city')
            address = request.POST.get('address')
            district = request.POST.get('district')
            
            # Check if email is being changed and if it's already in use
            if email != moderator.email:
                if Users.objects.filter(email=email).exists():
                    return JsonResponse({'success': False, 'errors': {'email': 'This email is already in use. Please try another.'}})
            
            # Validate company name
            if not re.match(r'^[A-Za-z][A-Za-z\s]*$', company):
                return JsonResponse({'success': False, 'errors': {'company': 'Company name should only contain letters and spaces, and start with a letter.'}})
            
            try:
                with transaction.atomic():
                    moderator.first_name = first_name
                    moderator.last_name = last_name
                    moderator.mobile = mobile
                    moderator.email = email
                    moderator.company = company
                    moderator.city = city
                    moderator.address = address
                    moderator.district = district
                    
                    if 'profile_image' in request.FILES:
                        moderator.profile_image = request.FILES['profile_image']
                    
                    moderator.save()
                    
                    # Update the associated User model
                    user = moderator.user
                    user.first_name = first_name
                    user.last_name = last_name
                    user.email = email
                    user.save()
                
                return JsonResponse({'success': True, 'message': 'Profile updated successfully'})
            except IntegrityError:
                return JsonResponse({'success': False, 'errors': {'email': 'This email is already in use. Please try another.'}})
        
        return render(request, 'mod_profile.html', {'moderator': moderator})
    
    except Moderator.DoesNotExist:
        return JsonResponse({'success': False, 'errors': {'general': 'Moderator profile not found'}})



def customer_details(request):
    customers = Customers.objects.select_related('user').all()
    return render(request, 'customer_details.html', {'customers': customers})



def mod_request(request):
    return render(request, 'mod_request.html')


def moderator_details(request):
    approved_moderators = Moderator.objects.filter(status='Approved')
    return render(request, 'moderator_details.html', {'moderators': approved_moderators})





@login_required
def mod_home(request):
    moderator = Moderator.objects.get(user=request.user)
    
    total_buses = Bus.objects.filter(moderator_id=moderator).count()
    total_agents = Agent.objects.filter(moderator=moderator).count()
    total_reports = SafetyNotificationReport.objects.filter(agent__moderator=moderator).count()
    
    context = {
        'first_name': moderator.first_name,
        'last_name': moderator.last_name,
        'total_buses': total_buses,
        'total_agents': total_agents,
        'total_reports': total_reports,
    }
    
    return render(request, 'mod_home.html', context)



from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
from home.models import BusImage
@login_required
def add_bus(request):
    if request.method == 'POST':
        form = BusForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                moderator = Moderator.objects.get(user=request.user)
                bus = form.save(commit=False)
                bus.moderator_id = moderator
                bus.arrival_date = form.cleaned_data['arrival_date']
                bus.save()

                # Handle multiple image uploads
                bus_images = request.FILES.getlist('bus_images')
                for image in bus_images:
                    # Generate a unique filename
                    filename = f"bus_{bus.bus_id}_{image.name}"
                    path = default_storage.save(f'bus_images/{filename}', ContentFile(image.read()))
                    BusImage.objects.create(bus=bus, image=path)

                # Create DriversInfo instance
                try:
                    driver_info = DriversInfo.objects.create(
                        bus=bus,
                        name=form.cleaned_data['driver_name'],
                        license=request.FILES['driver_license'],
                        email=form.cleaned_data['driver_email'],
                        contact_number=form.cleaned_data['driver_contact'],
                        image=request.FILES['driver_image']
                    )
                except IntegrityError:
                    bus.delete()  # Delete the bus since we couldn't create the driver
                    return JsonResponse({'success': False, 'error': {'driver_email': ['Driver email already exists']}})

                return JsonResponse({'success': True, 'message': 'Bus and driver information added successfully'})
            except ObjectDoesNotExist:
                return JsonResponse({'success': False, 'error': {'general': ['You are not authorized to add a bus']}})
            except IntegrityError as e:
                if 'bus_number' in str(e):
                    return JsonResponse({'success': False, 'error': {'bus_number': ['Bus number already exists']}})
                else:
                    return JsonResponse({'success': False, 'error': {'general': [f'An error occurred while saving the bus: {str(e)}']}})
        else:
            return JsonResponse({'success': False, 'error': form.errors})
    else:
        return JsonResponse({'success': False, 'error': {'general': ['Invalid request method']}})




@require_POST
def update_profile(request):
    try:
        customer = Customers.objects.get(email=request.user.email)

        # Server-side validation
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        address = request.POST.get('address', '').strip()

        errors = {}

        if not first_name or re.search(r'\d', first_name):
            errors['first_name'] = "First name is required and should not contain numbers."
        if not last_name or re.search(r'\d', last_name):
            errors['last_name'] = "Last name is required and should not contain numbers."
        if not email:
            errors['email'] = "Email is required."
        else:
            try:
                validate_email(email)
                # Check if email already exists for another user
                if Customers.objects.exclude(email=request.user.email).filter(email=email).exists():
                    errors['email'] = "This email is already taken."
            except ValidationError:
                errors['email'] = "Please enter a valid email address."
        if not phone_number or not phone_number.isdigit() or len(phone_number) != 10:
            errors['phone_number'] = "Please enter a valid 10-digit phone number."
        if not address:
            errors['address'] = "Address is required."

        # Validate profile picture
        if 'profile_picture' in request.FILES:
            file = request.FILES['profile_picture']
            if not file.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                errors['profile_picture'] = "Please upload an image file (jpg, jpeg, png, or gif)."

        if errors:
            return JsonResponse({'success': False, 'errors': errors})

        customer.first_name = first_name
        customer.last_name = last_name
        customer.email = email
        customer.phone = phone_number
        customer.address = address

        profile_picture_url = None
        if 'profile_picture' in request.FILES:
            file = request.FILES['profile_picture']
            file_name = default_storage.save(os.path.join('profile_pictures', file.name), ContentFile(file.read()))
            customer.profile_picture = file_name
            profile_picture_url = customer.profile_picture.url

        customer.save()

        # Update the associated User model
        user = customer.user
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()

        create_notification(request.user, "Your profile has been updated.")

        return JsonResponse({
            'success': True,
            'first_name': customer.first_name,
            'last_name': customer.last_name,
            'email': customer.email,
            'phone_number': customer.phone,
            'address': customer.address,
            'profile_picture_url': profile_picture_url
        })

    except Customers.DoesNotExist:
        return JsonResponse({'success': False, 'errors': {'general': "Customer profile not found."}})
    except Exception as e:
        return JsonResponse({'success': False, 'errors': {'general': str(e)}})


@login_required
def booking_page(request):
    return render(request, 'booking.html')



from django.db.models import Case, When, Value, IntegerField

from django.core.serializers import serialize
from django.http import JsonResponse
import json

from django.core.serializers.json import DjangoJSONEncoder

@login_required
def buses_added_by_moderator(request):
    try:
        moderator = Moderator.objects.get(user=request.user)
        buses = Bus.objects.filter(moderator_id=moderator).select_related('driver_info').prefetch_related('feedbacks')
        
        # Update status for each bus
        for bus in buses:
            bus.update_status()
            bus.can_reschedule = bus.can_reschedule()  # Add this line
        
        # Handle filtering
        status_filter = request.GET.get('status')
        if status_filter in ['active', 'under_maintenance']:
            buses = buses.filter(status=status_filter)

        # Handle sorting
        sort_by = request.GET.get('sort_by', 'status')
        if sort_by == 'status':
            buses = buses.annotate(
                status_order=Case(
                    When(status='active', then=Value(1)),
                    When(status='under_maintenance', then=Value(2)),
                    default=Value(3),
                    output_field=IntegerField(),
                )
            ).order_by('status_order')
        elif sort_by == 'date':
            buses = buses.order_by('-date')
        elif sort_by == 'name':
            buses = buses.order_by('bus_name')

        for bus in buses:
            bus.feedback_count = bus.feedbacks.count()
            bus.avg_rating = bus.average_rating()

        # Fetch locations data
        locations = list(Location.objects.all().values('source', 'source_code', 'destination', 'destination_code', 'stops'))
        locations_json = json.dumps(locations, cls=DjangoJSONEncoder)
        
        context = {
            'buses': buses,
            'first_name': moderator.first_name,
            'last_name': moderator.last_name,
            'current_status': status_filter,
            'current_sort': sort_by,
            'locations_json': locations_json,
        }
        return render(request, 'buses_added_by_moderator.html', context)
    except Moderator.DoesNotExist:
        return redirect('index')
    


def calculate_duration(departure_time, arrival_time):
    # Convert time objects to datetime objects for easier calculation
    departure = datetime.combine(datetime.min, departure_time)
    arrival = datetime.combine(datetime.min, arrival_time)
    
    # If arrival is earlier than departure, assume it's the next day
    if arrival < departure:
        arrival += timedelta(days=1)
    
    duration = arrival - departure
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours}h {minutes}m"


def get_recommended_buses(user, available_buses):
    """
    Generate bus recommendations based on user's history and preferences.
    Returns a dict with bus_id as key and recommendation details as value.
    """
    recommendations = {}
    MAX_RECOMMENDATIONS = 2  # Maximum number of recommendations to show
    
    if not user.is_authenticated:
        return recommendations
        
    try:
        # First check if user has a customer profile
        try:
            customer = Customers.objects.get(user=user)
        except Customers.DoesNotExist:
            customer = None
        # Get user's booking history
        user_bookings = BusBooking.objects.filter(
            customer=customer,
            payment_status='Paid'
        ).select_related('bus').order_by('-booking_date')
        
        if not user_bookings.exists():
            # If user has no booking history, recommend highest rated buses
            highly_rated_buses = []
            for bus in available_buses:
                avg_rating = bus.average_rating()
                if avg_rating and avg_rating >= 4.5:
                    highly_rated_buses.append((bus, avg_rating))
            
            # Sort by rating and take top 2
            highly_rated_buses.sort(key=lambda x: x[1], reverse=True)
            for bus, rating in highly_rated_buses[:MAX_RECOMMENDATIONS]:
                recommendations[bus.bus_id] = {
                    'score': rating,
                    'reasons': ["Highly rated by travelers"]
                }
            return recommendations
        
        # Analyze user preferences from last 5 bookings
        recent_bookings = user_bookings[:5]
        preferred_times = []
        preferred_bus_types = {}
        total_amount = 0
        
        for booking in recent_bookings:
            if booking.bus:
                # Track preferred times
                preferred_times.append(booking.bus.departure_time)
                
                # Track bus type frequency
                bus_type = booking.bus.bus_type
                preferred_bus_types[bus_type] = preferred_bus_types.get(bus_type, 0) + 1
                
                # Track spending
                total_amount += float(booking.bus.ticket_price)
        
        avg_price = total_amount / len(recent_bookings)
        
        # Get most frequently booked bus type
        if preferred_bus_types:
            favorite_bus_type = max(preferred_bus_types.items(), key=lambda x: x[1])[0]
        else:
            favorite_bus_type = None
            
        # Score and rank available buses
        scored_buses = []
        for bus in available_buses:
            score = 0
            reasons = []
            
            # Check bus type match
            if favorite_bus_type and bus.bus_type == favorite_bus_type:
                score += 3
                reasons.append("Matches your preferred bus type")
            
            # Check price similarity (within 15% of average spending)
            price = float(bus.ticket_price)
            price_diff_percent = abs(price - avg_price) / avg_price * 100
            if price_diff_percent <= 15:
                score += 2
                reasons.append("Within your usual price range")
            
            # Check ratings
            avg_rating = bus.average_rating()
            if avg_rating:
                if avg_rating >= 4.5:
                    score += 3
                    reasons.append("Highly rated by travelers")
                elif avg_rating >= 4.0:
                    score += 1
            
            # Check time preference (within 1.5 hours of usual booking time)
            if preferred_times:
                for pref_time in preferred_times:
                    time_diff = abs((bus.departure_time.hour * 60 + bus.departure_time.minute) - 
                                  (pref_time.hour * 60 + pref_time.minute))
                    if time_diff <= 90:  # Within 1.5 hours
                        score += 2
                        reasons.append("Departure time matches your preference")
                        break
            
            # Only consider high-scoring buses (minimum 6 points)
            if score >= 6:
                scored_buses.append({
                    'bus_id': bus.bus_id,
                    'score': score,
                    'reasons': reasons[:2]  # Keep top 2 reasons
                })
        
        # Sort by score and take top recommendations
        scored_buses.sort(key=lambda x: x['score'], reverse=True)
        for bus_data in scored_buses[:MAX_RECOMMENDATIONS]:
            recommendations[bus_data['bus_id']] = {
                'score': bus_data['score'],
                'reasons': bus_data['reasons']
            }
            
    except Exception as e:
        logger.error(f"Error in get_recommended_buses: {str(e)}")
        
    return recommendations

def bus_list(request):
    bus_id = request.GET.get('bus_id')
    package_id = request.GET.get('package_id')
    num_people = request.GET.get('num_people')
    package_amount = request.GET.get('package_amount')
    
    if request.method == 'POST':
        # Handle direct search case
        source = request.POST.get('departure_location')
        destination = request.POST.get('destination_location')
        date_str = request.POST.get('date')
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        # Handle package-based redirection
        if bus_id:
            # If we have a specific bus_id, get that bus's details
            try:
                bus = Bus.objects.get(bus_id=bus_id)
                source = bus.departure_location
                destination = bus.destination_location
                date = bus.date
            except Bus.DoesNotExist:
                return render(request, 'bus_list.html', {'error': 'Bus not found'})
        else:
            return render(request, 'bus_list.html')
    
    # Fetch bus data based on the source, destination, and date
    # Exclude buses with status 'under_maintenance'
    buses = Bus.objects.filter(
        departure_location__icontains=source,
        destination_location__icontains=destination,
        date=date,
        status='active'
    ).prefetch_related('feedbacks')

    # If bus_id is provided, filter for that specific bus
    if bus_id:
        buses = buses.filter(bus_id=bus_id)

    # Calculate duration and available seats for each bus
    for bus in buses:
        bus.duration = calculate_duration(bus.departure_time, bus.arrival_time)
        
        # Calculate available seats
        booked_seats = BusBooking.objects.filter(
            bus=bus, 
            payment_status__in=['Paid', 'Pending']
        ).aggregate(total_booked=Sum('num_tickets'))['total_booked'] or 0
        
        bus.available_seats = max(0, bus.seating_capacity - booked_seats)
        
        # Get all booked seat numbers
        booked_seat_numbers = BusBooking.objects.filter(
            bus=bus, 
            payment_status__in=['Paid', 'Pending']
        ).values_list('seat_booked', flat=True)
        
        bus.booked_seats = ','.join(seat for seats in booked_seat_numbers for seat in seats.split(','))
        
        bus.avg_rating = bus.average_rating()
        bus.rating_distribution = bus.rating_distribution()
        bus.recent_feedbacks = bus.get_recent_feedbacks()
        bus.liked_features = bus.get_liked_features()

    # Get recommendations if user is authenticated
    recommendations = get_recommended_buses(request.user, buses)
    
    # Convert QuerySet to list for sorting
    buses = list(buses)
    
    # Add recommendation info to buses and prepare for sorting
    for bus in buses:
        if bus.bus_id in recommendations:
            bus.is_recommended = True
            bus.recommendation_reasons = recommendations[bus.bus_id]['reasons']
            bus.recommendation_score = recommendations[bus.bus_id]['score']
        else:
            bus.is_recommended = False
            bus.recommendation_reasons = []
            bus.recommendation_score = 0

    # Sort buses to put recommended ones first
    def sort_key(bus):
        return (0 if bus.is_recommended else 1, -bus.recommendation_score)
    
    buses = sorted(buses, key=sort_key)

    context = {
        'source': source,
        'destination': destination,
        'date': date,
        'buses': buses,
        'package_id': package_id,
        'num_people': num_people,
        'package_amount': package_amount,
        'auto_open_bus_id': bus_id
    }
    return render(request, 'bus_list.html', context)

def get_booked_seats(request, bus_id):
    if bus_id == 'undefined':
        return JsonResponse({'error': 'Invalid bus ID'}, status=400)
    
    try:
        bus = get_object_or_404(Bus, pk=bus_id)
        booked_seats = BusBooking.objects.filter(
            bus=bus,
            payment_status__in=['Paid', 'Pending']
        ).values_list('seat_booked', flat=True)
        
        all_booked_seats = []
        for seats in booked_seats:
            all_booked_seats.extend(seats.split(','))
        
        return JsonResponse({'booked_seats': all_booked_seats})
    except Bus.DoesNotExist:
        raise Http404("Bus does not exist")


import logging
logger = logging.getLogger(__name__)

@login_required
def bus_availability(request, bus_id):
    try:
        bus = Bus.objects.get(bus_id=bus_id)
        current_schedule_version = bus.schedule_version
        bookings = BusBooking.objects.filter(
            bus=bus, 
            payment_status='Paid',
            schedule_version=current_schedule_version
        )
        booked_seats = set()
        for booking in bookings:
            booked_seats.update(booking.seat_booked.split(','))
        
        available_seats = bus.seating_capacity - len(booked_seats)
        
        logger.info(f"Bus {bus_id} has {available_seats} available seats and {len(booked_seats)} booked seats")
        
        return JsonResponse({
            'available_seats': available_seats,
            'booked_seats': list(booked_seats)
        })
    except Bus.DoesNotExist:
        logger.error(f"Bus with id {bus_id} not found")
        return JsonResponse({'error': 'Bus not found'}, status=404)
    except Exception as e:
        logger.error(f"Error in bus_availability for bus {bus_id}: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

import logging
from django.core.exceptions import ObjectDoesNotExist
logger = logging.getLogger(__name__)

from django.http import JsonResponse
from django.db.models import Avg, Count
from home.models import Feedback, Bus
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from home.models import PackageBooking

def all_bus_reviews(request, bus_id):
    try:
        bus = Bus.objects.get(bus_id=bus_id)
        reviews = Feedback.objects.filter(bus=bus).order_by('-created_at')
        
        overall_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
        rating_distribution = reviews.values('rating').annotate(count=Count('rating')).order_by('-rating')
        
        distribution = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        total_reviews = reviews.count()
        
        for item in rating_distribution:
            distribution[item['rating']] = (item['count'] / total_reviews) * 100 if total_reviews > 0 else 0

        review_data = [
            {
                'user_name': review.booking.customer.first_name,
                'date': review.created_at.strftime('%d-%m-%Y'),
                'rating': review.rating,
                'comment': review.comment,
                'could_be_better': review.improvements
            }
            for review in reviews
        ]

        return JsonResponse({
            'overall_rating': overall_rating,
            'rating_distribution': [distribution[i] for i in range(5, 0, -1)],
            'reviews': review_data
        })
    except Bus.DoesNotExist:
        return JsonResponse({'error': 'Bus not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@transaction.atomic
def deactivate_moderator(request, moderator_id):
    if request.method == 'POST':
        moderator = get_object_or_404(Moderator, moderator_id=moderator_id)
        user = moderator.user
        
        # Delete all buses associated with this moderator
        Bus.objects.filter(moderator_id=moderator).delete()
        
        # Delete the moderator and associated user
        moderator.delete()
        user.delete()
        
        messages.success(request, f"Moderator {moderator.first_name} {moderator.last_name} has been deactivated and removed from the system, along with all their associated buses.")
    
    return redirect('moderator_details')


def add_locations(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            source = data.get('source')
            source_code = data.get('source_code')
            destination = data.get('destination')
            destination_code = data.get('destination_code')
            stops = data.get('stops', [])

            # Create new location without checking for duplicates
            location = Location.objects.create(
                source=source,
                source_code=source_code,
                destination=destination,
                destination_code=destination_code,
                stops=','.join(stops)
            )
            return JsonResponse({'success': True, 'message': 'Location added successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error adding location: {str(e)}'})
    
    return render(request, 'add_locations.html')

@require_POST
@transaction.atomic
def upload_excel(request):
    if 'excelFile' not in request.FILES:
        return JsonResponse({'success': False, 'message': 'No file was uploaded'})

    excel_file = request.FILES['excelFile']
    
    try:
        # Save the uploaded file temporarily
        file_name = default_storage.save('temp_excel_upload.xlsx', ContentFile(excel_file.read()))
        file_path = default_storage.path(file_name)
        
        # Process the Excel file
        df = pd.read_excel(file_path)
        
        # Check if required columns exist
        required_columns = ['source', 'source_code', 'destination', 'destination_code', 'stops']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing columns in Excel file: {', '.join(missing_columns)}")
        
        locations_added = 0
        locations_updated = 0
        for index, row in df.iterrows():
            # Normalize stops: split, strip, sort, and rejoin
            new_stops = sorted([stop.strip() for stop in row['stops'].split(',') if stop.strip()])
            new_stops_str = ','.join(new_stops)

            # Check if an exactly identical location already exists
            existing_location = Location.objects.filter(
                source=row['source'],
                source_code=row['source_code'],
                destination=row['destination'],
                destination_code=row['destination_code'],
                stops=new_stops_str
            ).first()

            if existing_location:
                # Delete the existing entry
                existing_location.delete()
                locations_updated += 1
                logger.info(f"Updated entry: {row['source']} to {row['destination']} with stops: {new_stops_str}")
            else:
                locations_added += 1
                logger.info(f"Added new entry: {row['source']} to {row['destination']} with stops: {new_stops_str}")

            # Create new location (whether it's an update or a new entry)
            Location.objects.create(
                source=row['source'],
                source_code=row['source_code'],
                destination=row['destination'],
                destination_code=row['destination_code'],
                stops=new_stops_str
            )
        
        # Delete the temporary file
        default_storage.delete(file_name)
        
        message = f'{locations_added} new locations added. {locations_updated} locations updated.'
        logger.info(message)
        return JsonResponse({'success': True, 'message': message})
    except Exception as e:
        logger.error(f"Error processing Excel file: {str(e)}")
        return JsonResponse({'success': False, 'message': f'Error processing Excel file: {str(e)}'})


def get_locations(request):
    try:
        locations = Location.objects.all()
        locations_data = []
        for location in locations:
            locations_data.append({
                'source': location.source,
                'source_code': location.source_code,
                'destination': location.destination,
                'destination_code': location.destination_code,
                'stops': location.stops.split(',') if location.stops else []  # Assuming stops are stored as comma-separated string
            })
        return JsonResponse({'success': True, 'locations': locations_data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error fetching locations: {str(e)}'})



def create_notification(user, message):
    Notification.objects.create(user=user, message=message)



@login_required
def booking_confirmation(request, booking_id):
    booking = get_object_or_404(BusBooking, booking_id=booking_id, customer__user=request.user)
    
    # Check if this is associated with a package booking
    try:
        package_booking = PackageBooking.objects.get(bus_booking=booking)
        is_package_booking = True
    except PackageBooking.DoesNotExist:
        package_booking = None
        is_package_booking = False
    
    context = {
        'booking': booking,
        'bus': booking.bus,
        'customer': booking.customer,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY
    }
    
    if is_package_booking:
        package_details = {
            'num_people': package_booking.num_travelers,
            'amount_per_person': float(package_booking.package.price),  # Use package price directly
            'total_amount': float(package_booking.package.price) * package_booking.num_travelers,  # Calculate total package amount
            'bus_amount': float(booking.total_amount)  # Convert to float for consistency
        }
        context['package_details'] = package_details
        context['package_booking'] = package_booking
    
    return render(request, 'booking_confirmation.html', context)

stripe.api_key = settings.STRIPE_SECRET_KEY

@method_decorator(csrf_exempt, name='dispatch')
class CreateCheckoutSessionView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            booking_id = data.get('booking_id')
            passengers = data.get('passengers', [])
            package_details = data.get('package_details')

            logger.info(f"Received data: {data}")

            if not booking_id:
                logger.error("400 error: Booking ID is required")
                return JsonResponse({'error': 'Booking ID is required'}, status=400)

            try:
                booking = get_object_or_404(BusBooking, booking_id=booking_id)
                customer = booking.customer

                # Save passenger data
                booking.passenger_details = json.dumps(passengers)
                booking.save()

                # Calculate total amount
                total_amount = int(booking.total_amount)  # Use the total amount that's already calculated
                
                # Build detailed description
                bus_details = (
                    "🚌 BUS DETAILS\n"
                    "-------------------\n"
                    f"Bus:         {booking.bus.bus_name}\n"
                    f"Seats:       {booking.seat_booked}\n"
                    f"Price/Seat:  ₹{int(booking.bus.ticket_price):,}\n"
                    f"Bus Total:   ₹{int(booking.bus.ticket_price) * len(booking.seat_booked.split(',')):,}\n\n"
                )
                
                # If this is a package booking, add package details
                package_description = ""
                detailed_description = bus_details
                if package_details:
                    logger.info(f"Package details found: {package_details}")
                    try:
                        package_booking = PackageBooking.objects.get(bus_booking=booking)
                        package_booking.passenger_details = json.dumps(passengers)
                        package_booking.save()
                        
                        package_amount = int(package_booking.package.price) * package_booking.num_travelers
                        package_description = " (Including Package)"
                        detailed_description += (
                            "🏖️ PACKAGE DETAILS\n"
                            "-------------------\n"
                            f"Package:      {package_booking.package.title}\n"
                            f"Travelers:    {package_booking.num_travelers}\n"
                            f"Price/Person: ₹{int(package_booking.package.price):,}\n"
                            f"Pack. Total:  ₹{package_amount:,}\n\n"
                        )
                    except PackageBooking.DoesNotExist:
                        logger.warning("Package details provided but no PackageBooking found")
                
                detailed_description += (
                    "💰 TOTAL AMOUNT\n"
                    "-------------------\n"
                    f"₹{total_amount:,}"
                )
                
                # Create line items with detailed description
                line_items = [{
                    'price_data': {
                        'currency': 'inr',
                        'unit_amount': total_amount * 100,  # Convert to paise
                        'product_data': {
                            'name': f'Bus Booking #{booking.booking_id}{package_description}',
                            'description': detailed_description,
                        },
                    },
                    'quantity': 1,
                }]
                
                # Create Stripe checkout session
                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=line_items,
                    mode='payment',
                    customer_email=customer.email,  # Email is set here at the root level
                    client_reference_id=booking_id,
                    success_url=request.build_absolute_uri(reverse('payment_success')) + f'?session_id={{CHECKOUT_SESSION_ID}}&booking_id={booking_id}',
                    cancel_url=request.build_absolute_uri(reverse('booking_cancel')),
                    payment_intent_data={
                        'shipping': {
                            'address': {
                                'line1': customer.address,
                                'city': customer.city,
                                'state': customer.district,
                                'postal_code': customer.postal_code,
                                'country': 'IN',
                            },
                            'name': f"{customer.first_name} {customer.last_name}",
                            'phone': customer.phone,
                        },
                    },
                )

                # Update the booking status to 'Processing'
                booking.payment_status = 'Processing'
                booking.save()

                return JsonResponse({'sessionId': checkout_session.id})
            except Exception as e:
                logger.error(f"Error creating checkout session: {str(e)}")
                return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Error in CreateCheckoutSessionView: {str(e)}")
            return JsonResponse({'error': str(e)}, status=400)
    





@login_required
def save_passenger_details(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            booking_id = data.get('booking_id')
            passenger_details = data.get('passenger_details')
            
            booking = BusBooking.objects.get(booking_id=booking_id, customer__user=request.user)
            
            # Save passenger details to bus booking
            booking.passenger_details = passenger_details
            booking.save()
            
            # If this is a package booking, also save to package booking
            try:
                package_booking = PackageBooking.objects.get(bus_booking=booking)
                package_booking.passenger_details = passenger_details
                package_booking.save()
            except PackageBooking.DoesNotExist:
                pass  # Not a package booking, continue
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def booking_success(request):
    # Get the latest paid booking for the user
    booking = BusBooking.objects.filter(customer__user=request.user, payment_status='Paid').latest('booking_date')
    payment = Payment.objects.filter(booking=booking).first()
    return render(request, 'booking_success.html', {'booking': booking, 'payment': payment})


@login_required
def booking_cancel(request):
    booking_id = request.session.get('temp_booking_id')
    if booking_id:
        try:
            booking = BusBooking.objects.get(booking_id=booking_id)
            booking.payment_status = 'Cancelled'
            booking.save()
            del request.session['temp_booking_id']
        except BusBooking.DoesNotExist:
            pass
    return render(request, 'booking_cancel.html')



from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
def your_bookings(request):
    paid_bookings = BusBooking.objects.filter(
        customer__user=request.user,
        payment_status='Paid'
    ).select_related('bus', 'customer').order_by('-booking_date')

    booking_data = []
    for booking in paid_bookings:
        payment = Payment.objects.filter(booking=booking, status='completed').first()
        
        if payment:
            arrival_date = booking.bus.arrival_date or booking.bus.date
            arrival_datetime = timezone.make_aware(
                datetime.combine(arrival_date, booking.bus.arrival_time),
                timezone.get_current_timezone()
            )
            
            passenger_details = json.loads(booking.passenger_details) if booking.passenger_details else []
            
            booking_data.append({
                'id': booking.booking_id,
                'departure_location': booking.departure_location,
                'destination': booking.destination,
                'date': booking.bus.date.strftime('%Y-%m-%d'),
                'departure_time': booking.bus.departure_time.strftime('%H:%M'),
                'arrival_time': booking.bus.arrival_time.strftime('%H:%M'),
                'arrival_date': arrival_datetime.strftime('%Y-%m-%d'),
                'bus_operator': booking.bus.bus_name,
                'seat_numbers': booking.seat_booked,
                'booked_person': {
                    'name': f"{booking.customer.first_name} {booking.customer.last_name}",
                    'email': booking.customer.email,
                    'phone': booking.customer.phone,
                },
                'passenger_details': passenger_details,
                'price_paid': str(booking.total_amount),
                'payment_status': 'Paid',
                'booking_date': booking.booking_date.strftime('%Y-%m-%d %H:%M'),
                'payment_method': payment.payment_method,
                'payment_date': payment.payment_date.strftime('%Y-%m-%d %H:%M'),
                'ticket_number': booking.ticket_number,
                'can_submit_feedback': timezone.now() > arrival_datetime,
            })

    return render(request, 'your_bookings.html', {'bookings': json.dumps(booking_data, cls=DjangoJSONEncoder)})



from django.core.serializers.json import DjangoJSONEncoder
from django.forms.models import model_to_dict

def e_ticket(request):
    booking_id = request.GET.get('booking_id')
    if booking_id:
        booking = get_object_or_404(BusBooking, booking_id=booking_id, customer__user=request.user)
        
        booking_dict = {
            'booking_id': booking.booking_id,
            'departure_location': booking.departure_location,
            'destination': booking.destination,
            'departure_time': booking.bus.departure_time.strftime('%H:%M'),
            'arrival_time': booking.bus.arrival_time.strftime('%H:%M'),
            'date': booking.bus.date.strftime('%Y-%m-%d'),
            'bus_operator': booking.bus.bus_name,
            'seat_numbers': booking.seat_booked,
            'booked_person': {
                'name': f"{booking.customer.first_name} {booking.customer.last_name}",
                'email': booking.customer.email,
                'phone': booking.customer.phone
            },
            'price_paid': str(booking.total_amount),
            'ticket_number': booking.ticket_number
        }
        
        try:
            passenger_details = json.loads(booking.passenger_details) if booking.passenger_details else []
        except json.JSONDecodeError:
            passenger_details = []

        context = {
            'booking': json.dumps(booking_dict, cls=DjangoJSONEncoder),
            'passenger_details': json.dumps(passenger_details)
        }

        # Check if the request is coming from a mobile device
        if request.GET.get('mobile') == 'true':
            # Render the e-ticket as a standalone page for mobile devices
            html = render_to_string('e_ticket.html', context)
            return HttpResponse(html)
        else:
            # Render the e-ticket normally for web browsers
            return render(request, 'e_ticket.html', context)
    return redirect('your_bookings')

@transaction.atomic
def payment_success(request):
    session_id = request.GET.get('session_id')
    booking_id = request.GET.get('booking_id')

    if not session_id or not booking_id:
        return redirect('booking_cancel')

    try:
        booking = BusBooking.objects.get(booking_id=booking_id)
        session = stripe.checkout.Session.retrieve(session_id)

        if session.payment_status == 'paid':
            booking.payment_status = 'Paid'
            booking.save()

            # Create a Payment record
            Payment.objects.create(
                booking=booking,
                stripe_payment_intent_id=session.payment_intent,
                amount=session.amount_total / 100,
                currency=session.currency,
                status='completed',
                payment_method='card',
            )

            # Clear the temporary booking session variable
            if 'temp_booking_id' in request.session:
                del request.session['temp_booking_id']

            try:
                # Generate PDF
                pdf = render_to_pdf('invoice_email.html', {'booking': booking})
                if pdf:
                    # Send email with PDF attachment
                    subject = 'Your Booking Invoice'
                    message = 'Please find attached your booking invoice.'
                    from_email = settings.DEFAULT_FROM_EMAIL
                    to_email = booking.customer.email

                    email = EmailMessage(subject, message, from_email, [to_email])
                    email.attach(f'invoice_{booking.ticket_number}.pdf', pdf, 'application/pdf')

                    try:
                        email.send()
                        logger.info(f"Invoice email sent to {to_email}")
                    except Exception as e:
                        logger.error(f"Failed to send invoice email: {str(e)}")
                else:
                    logger.error("Failed to generate PDF")

                return redirect('booking_success')
            except Exception as e:
                logger.error(f"Error in payment success: {str(e)}", exc_info=True)
                return redirect('booking_cancel')
        else:
            booking.payment_status = 'Failed'
            booking.save()
            return redirect('booking_cancel')
    except Exception as e:
        logger.error(f"Error processing payment: {str(e)}", exc_info=True)
        return redirect('booking_cancel')
    





def get_notifications(request):
    if request.user.is_authenticated:
        notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')[:5]
        data = [{
            'message': notif.message,
            'created_at': notif.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for notif in notifications]
        return JsonResponse({'notifications': data, 'count': len(data)})
    return JsonResponse({'notifications': [], 'count': 0})




def agent_registration(request):
    return render(request, 'agent_registration.html')


def get_moderator_details(request):
    email = request.GET.get('email')
    try:
        moderator = Moderator.objects.get(email=email)
        return JsonResponse({
            'success': True,
            'moderator_name': f"{moderator.first_name} {moderator.last_name}",
            'company': moderator.company,
            'location': moderator.city  # Assuming 'city' is used as location
        })
    except Moderator.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Moderator not found'
        })
    


Users = get_user_model()
@transaction.atomic
def register_agent(request):
    if request.method == 'POST':
        try:
            # Extract data from POST request
            first_name = request.POST.get('first-name')
            last_name = request.POST.get('last-name')
            email = request.POST.get('email')
            mobile = request.POST.get('mobile')
            password = request.POST.get('password')
            moderator_email = request.POST.get('moderator-email')
            company = request.POST.get('company')
            location = request.POST.get('location')
            document = request.FILES.get('document')

            # Validate password
            try:
                validate_password(password)
            except ValidationError as e:
                return JsonResponse({'success': False, 'message': ' '.join(e.messages)})

            moderator = Moderator.objects.get(email=moderator_email)
            
            # Check if user already exists
            if Users.objects.filter(email=email).exists():
                return JsonResponse({'success': False, 'message': 'User with this email already exists.'})

            # Create user
            user = Users.objects.create_user(
                username=email, 
                email=email, 
                password=password, 
                user_type='agent'
            )

            # Create agent with status 'Pending'
            agent = Agent.objects.create(
                user=user,
                moderator=moderator,
                first_name=first_name,
                last_name=last_name,
                email=email,
                mobile=mobile,
                company=company,
                location=location,
                document=document,
                status='Pending',
                user_type='agent'
            )

            return JsonResponse({'success': True, 'message': 'Your registration request has been submitted and is pending approval.'})

        except Moderator.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Moderator not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return render(request, 'agent_registration.html')


@login_required
def agent_requests(request):
    if not request.user.is_superuser:
        return redirect('login')
    
    pending_agents = Agent.objects.filter(status='Pending')
    
    if request.method == 'POST':
        agent_id = request.POST.get('agent_id')
        action = request.POST.get('action')
        
        if agent_id and action:
            agent = get_object_or_404(Agent, agent_id=agent_id)
            if action == 'approve':
                agent.status = 'Approved'
                agent.save()
                messages.success(request, f'Agent {agent.first_name} {agent.last_name} has been approved.')
            elif action == 'reject':
                agent.status = 'Rejected'
                agent.save()
                messages.error(request, f'Agent {agent.first_name} {agent.last_name} has been rejected.')
    
    return render(request, 'agent_request.html', {'pending_agents': pending_agents})



from django.utils import timezone

from django.core.serializers.json import DjangoJSONEncoder
def agent_welcome(request):
    agent = Agent.objects.get(user=request.user)
    moderator = agent.moderator

    current_date = timezone.now().date()

    bus_routes = Bus.objects.filter(
        moderator_id=moderator,
        date__gte=current_date
    ).values('departure_location', 'destination_location', 'date').distinct()

    # Check if the agent has a current job
    current_job = AgentJob.objects.filter(
        agent=agent,
        bus__arrival_date__gte=timezone.now()
    ).first()

    has_current_job = current_job is not None

    # Debug logging
    for route in bus_routes:
        print(f"Route: {route['departure_location']} to {route['destination_location']}, Date: {route['date']}")

    context = {
        'agent': agent,
        'moderator': moderator,
        'bus_routes': bus_routes,
        'current_date': current_date,
        'has_current_job': has_current_job,
    }
    return render(request, 'agent_welcome.html', context)


import logging

logger = logging.getLogger(__name__)

from django.utils import timezone

@login_required
@require_GET
def get_buses_with_stops(request):
    departure = request.GET.get('departure')
    destination = request.GET.get('destination')
    date_str = request.GET.get('date')
    
    logger.info(f"Received request for buses: departure={departure}, destination={destination}, date={date_str}")
    
    try:
        # Convert date string to date object
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Get the current date
        current_date = timezone.now().date()
        
        # Check if the selected date is in the past
        if date < current_date:
            return JsonResponse({'success': False, 'message': 'Please select a present or future date.'})
        
        # Get the agent's moderator
        agent = Agent.objects.get(user=request.user)
        logger.info(f"Agent: {agent.email}, Moderator: {agent.moderator.email}")
        
        buses = Bus.objects.filter(
            moderator_id=agent.moderator,
            departure_location=departure, 
            destination_location=destination,
            date=date
        )
        
        logger.info(f"Found {buses.count()} buses")
        
        if buses.exists():
            bus_data = []
            for bus in buses:
                stops = [stop.strip() for stop in bus.stops.split(',') if stop.strip()]
                bus_data.append({
                    'id': bus.bus_id,
                    'stops': stops
                })
            logger.info(f"Returning {len(bus_data)} buses")
            return JsonResponse({'success': True, 'buses': bus_data})
        else:
            logger.info("No buses found for the given criteria")
            return JsonResponse({'success': False, 'message': 'No buses currently available for the selected route. Please select another route.'})
    except Exception as e:
        logger.error(f"Error in get_buses_with_stops: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})
 
def bus_images(request, bus_id):
    try:
        bus = Bus.objects.get(bus_id=bus_id)
        
        image_data = []
        for bus_image in bus.images.all():
            image_data.append({
                'url': bus_image.image.url,
                'caption': f"Image of {bus.bus_name}"
            })

        return JsonResponse({
            'images': image_data
        })
    except Bus.DoesNotExist:
        return JsonResponse({'error': 'Bus not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def check_temporary_booking(request):
    temp_booking_id = request.session.get('temp_booking_id')
    if temp_booking_id:
        try:
            booking = BusBooking.objects.get(booking_id=temp_booking_id, payment_status='Temporary')
            return JsonResponse({
                'has_temporary_booking': True,
                'booking_confirmation_url': reverse('booking_confirmation', args=[booking.booking_id])
            })
        except BusBooking.DoesNotExist:
            del request.session['temp_booking_id']
    return JsonResponse({'has_temporary_booking': False})

@login_required
@require_http_methods(["POST"])
def cancel_temporary_booking(request):
    temp_booking_id = request.session.get('temp_booking_id')
    logger.info(f"Attempting to cancel temporary booking: {temp_booking_id}")
    if temp_booking_id:
        try:
            booking = BusBooking.objects.get(booking_id=temp_booking_id, payment_status='Pending')
            logger.info(f"Found booking to cancel: {temp_booking_id}")
            booking.delete()
            logger.info(f"Deleted booking: {temp_booking_id}")
            del request.session['temp_booking_id']
            return JsonResponse({'success': True})
        except BusBooking.DoesNotExist:
            logger.warning(f"Booking not found for cancellation: {temp_booking_id}")
    else:
        logger.warning("No temporary booking ID in session")
    return JsonResponse({'success': False})

@login_required
def save_additional_passengers(request, booking_id):
    if request.method == 'POST':
        booking = get_object_or_404(BusBooking, booking_id=booking_id, customer__user=request.user)
        additional_passengers = json.loads(request.body).get('additional_passengers', [])
        booking.additional_passengers = json.dumps(additional_passengers)
        booking.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)

@login_required
@require_POST
@transaction.atomic
def create_booking(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            bus = Bus.objects.get(bus_id=data['bus_id'])
            customer = Customers.objects.get(user=request.user)
            
            # Create the bus booking first (this remains unchanged for both types)
            bus_booking = BusBooking(
                customer=customer,
                bus=bus,
                seat_booked=data['seats'],
                num_tickets=data['num_tickets'],
                departure_location=data['departure_location'],
                destination=data['destination'],
                total_amount=data['total_amount'],
                schedule_version=bus.schedule_version
            )
            bus_booking.save()

            # If this is a package booking, create package booking entry
            if 'package_id' in data:
                package = TourPackage.objects.get(id=data['package_id'])
                package_booking = PackageBooking(
                    package=package,
                    customer=customer,
                    bus=bus,
                    bus_booking=bus_booking,  # Link to bus booking
                    num_travelers=data['num_people'],
                    seat_numbers=data['seats'],
                    total_amount=float(data['total_amount']) + float(data['package_amount']),  # Combined bus and package amount
                    schedule_version=bus.schedule_version
                )
                package_booking.save()
            
            # Store the booking ID in the session
            request.session['temp_booking_id'] = bus_booking.booking_id
            
            return JsonResponse({
                'success': True,
                'redirect_url': reverse('booking_confirmation', args=[bus_booking.booking_id])
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})
