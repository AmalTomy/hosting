from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from ..models import TourPackage, PackageDay, PackageActivity, PackageImage, PackagePolicy, Bus, BusBooking, TravelReport, Moderator, Agent, SafetyNotificationReport
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
from datetime import datetime
from django.db.models import Sum
from datetime import timedelta

@login_required
def mod_addpackage(request):
    if request.method == 'POST':
        try:
            # Create the main package
            package = TourPackage.objects.create(
                title=request.POST.get('title'),
                destination=request.POST.get('destination'),
                duration_nights=request.POST.get('duration_nights'),
                duration_days=request.POST.get('duration_days'),
                overview=request.POST.get('overview'),
                price=request.POST.get('price'),
                category=request.POST.get('category'),
                hotel_category=request.POST.get('hotel_category'),
                has_bus='flights' in request.POST.getlist('features[]'),
                has_hotel='hotel' in request.POST.getlist('features[]'),
                has_meals='meals' in request.POST.getlist('features[]'),
                created_by=request.user
            )

            # Handle main image
            if request.FILES.get('main_image'):
                package.main_image = request.FILES['main_image']
                package.save()

            # Handle gallery images
            if request.FILES.getlist('gallery_images[]'):
                for image in request.FILES.getlist('gallery_images[]'):
                    PackageImage.objects.create(
                        package=package,
                        image=image
                    )

            # Create package policy
            PackagePolicy.objects.create(
                package=package,
                cancellation_policy=request.POST.get('cancellation_policy'),
                terms_conditions=request.POST.get('terms_conditions')
            )

            # Handle itinerary days
            day_count = 1
            while f'day{day_count}_title' in request.POST:
                day = PackageDay.objects.create(
                    package=package,
                    day_number=day_count,
                    title=request.POST.get(f'day{day_count}_title'),
                    meals=request.POST.get(f'day{day_count}_meals')
                )

                # Handle activities for each day
                activity_count = 1
                while f'day{day_count}_activity{activity_count}_title' in request.POST:
                    PackageActivity.objects.create(
                        day=day,
                        time=request.POST.get(f'day{day_count}_activity{activity_count}_time'),
                        title=request.POST.get(f'day{day_count}_activity{activity_count}_title'),
                        description=request.POST.get(f'day{day_count}_activity{activity_count}_description'),
                        order=activity_count
                    )
                    activity_count += 1

                day_count += 1

            return JsonResponse({
                'success': True,
                'message': 'Package created successfully!'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)

    return render(request, 'mod_addpackage.html')

def package(request):
    # Get all active packages
    packages = TourPackage.objects.filter(is_active=True)
    
    # Get bus_id from query parameter
    bus_id = request.GET.get('bus_id')
    destination = None
    
    if bus_id and bus_id.strip():  # Check if bus_id is not empty
        try:
            # Get the bus using bus_id field
            bus = get_object_or_404(Bus, bus_id=bus_id)
            # Update packages that don't have a bus assigned
            packages.filter(bus__isnull=True).update(bus=bus)
            
            # Filter packages by the bus's destination
            destination = bus.destination_location
            packages = packages.filter(destination=destination)
        except (Bus.DoesNotExist, ValueError):
            pass
    
    # Get counts for each category
    solo_count = packages.filter(category='solo').count()
    group_count = packages.filter(category='group').count()
    family_count = packages.filter(category='family').count()
    
    # Get selected category from query parameter (default to 'solo')
    selected_category = request.GET.get('category', 'solo').lower()
    
    return render(request, 'packages.html', {
        'packages': packages,  # Pass all packages to template
        'destination': request.session.get('destination_location', 'Your Destination'),
        'solo_count': solo_count,
        'group_count': group_count,
        'family_count': family_count,
        'selected_category': selected_category,
        'bus_id': bus_id  # Pass bus_id to template
    })

def package_details(request, package_id):
    package = get_object_or_404(TourPackage, id=package_id, is_active=True)
    package_days = package.days.all().order_by('day_number')
    package_images = package.gallery_images.all()
    package_policy = package.policy
    
    # Get bus_id from URL parameter and validate it
    bus_id = request.GET.get('bus_id')
    cancellation_deadline = None
    
    # If we have a bus_id, associate the package with the bus
    if bus_id and bus_id.strip():  # Check if bus_id is not empty
        try:
            bus = Bus.objects.get(bus_id=bus_id)  # Using bus_id field
            if not package.bus:
                package.bus = bus
                package.save()
            
            # Calculate cancellation deadline (1 day before departure)
            if bus.date:
                cancellation_deadline = bus.date - timezone.timedelta(days=1)
        except (Bus.DoesNotExist, ValueError):
            pass
    
    # If package has a bus (either from URL or previously assigned), use its date
    if not cancellation_deadline and package.bus and package.bus.date:
        cancellation_deadline = package.bus.date - timezone.timedelta(days=1)
    
    return render(request, 'package_details.html', {
        'package': package,
        'package_days': package_days,
        'package_images': package_images,
        'package_policy': package_policy,
        'cancellation_deadline': cancellation_deadline
    })

def get_destinations(request):
    if request.user.user_type != 'moderator':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    # Get unique destinations from active buses for this moderator
    destinations = Bus.objects.filter(
        moderator_id=request.user.moderator,
        status='active'  # Make sure this matches exactly with your Bus model's status field
    ).values_list('destination_location', flat=True).distinct()
    
    return JsonResponse({'destinations': list(destinations)})

@login_required
def get_routes(request):
    print("Entering get_routes view")  # Debug print
    if request.user.user_type != 'moderator':
        print(f"Access denied for user type: {request.user.user_type}")  # Debug print
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        # Get all buses added by this moderator
        print(f"Getting buses for user: {request.user.email}")  # Debug print
        moderator = Moderator.objects.get(user=request.user)
        buses = Bus.objects.filter(moderator_id=moderator)
        print(f"Found {buses.count()} buses")  # Debug print
        
        # Extract unique sources and destinations
        sources = list(buses.values_list('departure_location', flat=True).distinct())
        destinations = list(buses.values_list('destination_location', flat=True).distinct())
        
        print(f"Sources: {sources}")  # Debug print
        print(f"Destinations: {destinations}")  # Debug print
        
        return JsonResponse({
            'sources': sources,
            'destinations': destinations
        })
    except Exception as e:
        print(f"Error in get_routes: {str(e)}")  # Debug print
        return JsonResponse({'error': str(e)}, status=500)

def mod_viewaddedpackages(request):
    packages = TourPackage.objects.filter(is_active=True, created_by=request.user)
    
    # Handle sorting by category
    category = request.GET.get('sort', '')
    if category in ['solo', 'group', 'family']:
        packages = packages.filter(category=category)
    
    packages = packages.order_by('-created_at')
    
    return render(request, 'mod_viewaddedpackages.html', {
        'packages': packages,
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'selected_sort': category
    })

def disable_package(request, package_id):
    if request.method == 'POST':
        package = get_object_or_404(TourPackage, id=package_id, created_by=request.user)
        package.is_active = False
        package.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)

def your_activity(request):
    return render(request, 'your_activity.html')

@login_required
def generate_activity_report(request):
    if request.method == 'POST':
        start_month = request.POST.get('startMonth')
        end_month = request.POST.get('endMonth')
        report_type = request.POST.get('reportType')
        
        try:
            # Convert month strings to datetime objects
            start_date = datetime.strptime(start_month, '%Y-%m')
            end_date = datetime.strptime(end_month, '%Y-%m')
            
            # Set end_date to the last day of the month
            if end_date.month == 12:
                end_date = end_date.replace(year=end_date.year + 1, month=1, day=1)
            else:
                end_date = end_date.replace(month=end_date.month + 1, day=1)
            
            # Get data for the month range
            context = {
                'date_range': f"{start_date.strftime('%B %Y')} - {(end_date - timedelta(days=1)).strftime('%B %Y')}",
                'user': request.user,
                'generated_date': timezone.now(),
                'report_type': report_type
            }

            # Get bookings data if needed
            if report_type in ['all', 'bookings', 'payments']:
                bookings = BusBooking.objects.filter(
                    customer__user=request.user,
                    booking_date__gte=start_date,
                    booking_date__lt=end_date
                )
                context['bookings'] = bookings
                context['total_bookings'] = bookings.count()
                context['total_amount'] = bookings.aggregate(Sum('total_amount'))['total_amount__sum'] or 0

            # Get cancellations if needed
            if report_type in ['all', 'cancellations']:
                cancelled_bookings = BusBooking.objects.filter(
                    customer__user=request.user,
                    booking_date__gte=start_date,
                    booking_date__lt=end_date,
                    payment_status='Cancelled'
                )
                context['cancelled_bookings'] = cancelled_bookings
                context['total_cancellations'] = cancelled_bookings.count()

            # Get travel reports if needed
            if report_type in ['all', 'travel_reports']:
                travel_reports = TravelReport.objects.filter(
                    user=request.user,
                    submission_date__gte=start_date,
                    submission_date__lt=end_date
                )
                context['travel_reports'] = travel_reports
                context['total_reports'] = travel_reports.count()

            # Get payment history if needed
            if report_type in ['all', 'payments']:
                successful_payments = bookings.filter(payment_status='Success')
                context['successful_payments'] = successful_payments
                context['total_paid'] = successful_payments.aggregate(Sum('total_amount'))['total_amount__sum'] or 0

            # Generate PDF
            template = get_template('activity_report_pdf.html')
            html = template.render(context)
            
            # Create PDF
            result = BytesIO()
            pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
            
            if not pdf.err:
                # Generate filename with month range and report type
                filename = f"activity_report_{request.user.username}_{report_type}_{start_date.strftime('%Y%m')}_{end_date.strftime('%Y%m')}.pdf"
                
                # Prepare response
                response = HttpResponse(result.getvalue(), content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response

        except Exception as e:
            messages.error(request, f"Error generating report: {str(e)}")
            return redirect('your_activity')

    return redirect('your_activity')

@login_required
def mod_your_activities(request):
    print("Entering mod_your_activities view")  # Debug print
    print(f"Request method: {request.method}")  # Debug print
    print(f"Request path: {request.path}")  # Debug print
    print(f"User type: {request.user.user_type}")  # Debug print
    
    try:
        if request.user.user_type != 'moderator':
            print(f"User type is {request.user.user_type}")  # Debug print
            messages.error(request, "Access denied. You must be a moderator to view this page.")
            return redirect('mod_home')
        
        print(f"User is moderator: {request.user.username}")  # Debug print
        context = {
            'moderator_name': request.user.username,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name
        }
        response = render(request, 'mod_your_activities.html', context)
        print("Template rendered successfully")  # Debug print
        return response
    except Exception as e:
        print(f"Error in mod_your_activities: {str(e)}")  # Debug print
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('mod_home')

@login_required
def generate_mod_activity_report(request):
    if request.user.user_type != 'moderator':
        return HttpResponse('Access Denied')

    report_type = request.GET.get('report_type')
    source = request.GET.get('source', '')
    destination = request.GET.get('destination', '')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    format_type = request.GET.get('format', 'pdf')  # Default to PDF if not specified
    
    try:
        moderator = Moderator.objects.get(user=request.user)
        template_name = ''
        context = {'moderator': moderator}

        # Parse dates
        start_date = datetime.strptime(from_date, '%Y-%m-%d').date() if from_date else None
        end_date = (datetime.strptime(to_date, '%Y-%m-%d').date() + timedelta(days=1)) if to_date else None

        if report_type == 'buses':
            # Get all buses for this moderator
            buses = Bus.objects.filter(moderator_id=moderator)
            
            # Apply date filter if provided
            if start_date and end_date:
                buses = buses.filter(date__gte=start_date, date__lt=end_date)
            
            # Apply source filter if provided
            if source:
                buses = buses.filter(departure_location=source)
            
            # Apply destination filter if provided
            if destination:
                buses = buses.filter(destination_location=destination)
            
            template_name = 'bus_activity_report.html'
            context['buses'] = buses
            
        elif report_type == 'agents':
            agents = Agent.objects.filter(moderator=moderator)
            if start_date and end_date:
                agents = agents.filter(created_at__gte=start_date, created_at__lt=end_date)
            template_name = 'agent_activity_report.html'
            context['agents'] = agents
            
        elif report_type == 'packages':
            packages = TourPackage.objects.filter(created_by=request.user)
            if start_date and end_date:
                packages = packages.filter(created_at__gte=start_date, created_at__lt=end_date)
            template_name = 'package_activity_report.html'
            context['packages'] = packages

        # Add date range to context for display in report
        context.update({
            'from_date': from_date,
            'to_date': to_date,
            'report_type': report_type
        })
        
        # Generate HTML
        template = get_template(template_name)
        html = template.render(context)

        # Return based on format type
        if format_type == 'html' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return HttpResponse(html)
        else:
            # Create PDF
            result = BytesIO()
            pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
            
            if not pdf.err:
                response = HttpResponse(result.getvalue(), content_type='application/pdf')
                filename = f"{report_type}_report_{from_date}_to_{to_date}.pdf"
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
            
            return HttpResponse('Error generating PDF', status=500)
        
    except Exception as e:
        error_msg = f'Error: {str(e)}'
        if format_type == 'html' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return HttpResponse(f'<div class="alert alert-danger">{error_msg}</div>')
        return HttpResponse(error_msg, status=500)

@login_required
def generate_agent_report(request):
    if request.user.user_type != 'agent':
        return HttpResponse('Access Denied')

    status = request.GET.get('status', '')
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    action = request.GET.get('action', 'preview')  # 'preview' or 'download'
    
    try:
        agent = Agent.objects.get(user=request.user)
        template_name = 'agent_report.html'
        context = {'agent': agent}

        # Get all reports for this agent
        reports = SafetyNotificationReport.objects.filter(agent=agent)
        
        # Apply status filter if provided
        if status and status != 'all':
            reports = reports.filter(status=status)
            
        # Apply date range filter if provided
        if from_date and to_date:
            # Convert string dates to datetime.date objects
            from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
            to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
            # Add one day to to_date to include the entire day
            to_date = to_date + timedelta(days=1)
            
            reports = reports.filter(
                incident_datetime__date__gte=from_date,
                incident_datetime__date__lt=to_date
            )

        context['reports'] = reports
        context['selected_status'] = status
        context['from_date'] = from_date
        context['to_date'] = to_date

        # Generate PDF
        template = get_template(template_name)
        html = template.render(context)
        
        # Create PDF
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
        
        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            
            if action == 'download':
                # For download, set content disposition to attachment
                date_range = f"{from_date.strftime('%Y%m%d')}-{to_date.strftime('%Y%m%d')}"
                filename = f"safety_reports_{status}_{date_range}.pdf" if status else f"safety_reports_{date_range}.pdf"
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
            else:
                # For preview, set content disposition to inline and allow iframe display
                response['Content-Disposition'] = 'inline'
                response['X-Frame-Options'] = 'SAMEORIGIN'
                response['Content-Security-Policy'] = "frame-ancestors 'self'"
            
            return response
        
        return HttpResponse('Error generating PDF', status=500)
        
    except Agent.DoesNotExist:
        messages.error(request, "Agent profile not found.")
        return redirect('agent_welcome')

# Admin Report Generation Page View
@login_required
def admin_report_gen(request):
    if not request.user.is_authenticated or request.user.user_type != 'admin':
        messages.error(request, "You don't have permission to access this page.")
        return redirect('login')
    
    return render(request, 'admin_report_gen.html')

# Admin Report Generation Function
@login_required
def generate_admin_report(request):
    if not request.user.is_authenticated or request.user.user_type != 'admin':
        messages.error(request, "You don't have permission to access this page.")
        return redirect('login')
        
    if request.method == 'POST':
        report_type = request.POST.get('report_type')
        date_range_type = request.POST.get('date_range_type')
        file_format = request.POST.get('file_format')
        
        # Initialize date variables
        start_date = None
        end_date = None
        
        # Get date range based on selection type
        if date_range_type == 'custom':
            start_date_str = request.POST.get('start_date')
            end_date_str = request.POST.get('end_date')
            if start_date_str and end_date_str:
                # Use timezone.make_aware to handle timezone warnings
                from django.utils import timezone
                start_date = timezone.make_aware(datetime.strptime(start_date_str, '%Y-%m-%d'))
                end_date = timezone.make_aware(datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1))  # Include the end date
        elif date_range_type == 'month':
            start_month_str = request.POST.get('start_month')
            end_month_str = request.POST.get('end_month')
            if start_month_str and end_month_str:
                # Use timezone.make_aware to handle timezone warnings
                from django.utils import timezone
                start_date = timezone.make_aware(datetime.strptime(f"{start_month_str}-01", '%Y-%m-%d'))
                # Calculate the end of the month
                end_month_year, end_month = map(int, end_month_str.split('-'))
                if end_month == 12:
                    next_month_year = end_month_year + 1
                    next_month = 1
                else:
                    next_month_year = end_month_year
                    next_month = end_month + 1
                end_date = timezone.make_aware(datetime.strptime(f"{next_month_year}-{next_month:02d}-01", '%Y-%m-%d'))
        
        # If dates are not properly set, return error
        if not start_date or not end_date:
            messages.error(request, "Please select valid date range")
            return redirect('admin_report_gen')
            
        # Generate report based on type
        if report_type == 'bookings':
            queryset = BusBooking.objects.filter(booking_date__gte=start_date, booking_date__lt=end_date)
            filename = f"bus_bookings_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}"
            headers = ['Booking ID', 'Customer', 'Bus', 'Seats', 'Amount', 'Booking Date', 'Payment Status']
            data = [[
                booking.booking_id,
                str(booking.customer),
                str(booking.bus),
                booking.seat_booked,
                booking.total_amount,
                booking.booking_date.strftime('%Y-%m-%d %H:%M'),
                booking.payment_status
            ] for booking in queryset]
            
        elif report_type == 'customers':
            from ..models import Customers
            queryset = Customers.objects.all()
            if hasattr(Customers, 'user'):
                queryset = queryset.filter(user__date_joined__gte=start_date, user__date_joined__lt=end_date)
            filename = f"customers_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}"
            headers = ['ID', 'Name', 'Email', 'Phone', 'Address', 'Joined Date']
            data = []
            for customer in queryset:
                row = [
                    customer.customer_id,
                    f"{customer.first_name} {customer.last_name}",
                    customer.email,
                    customer.phone or 'N/A',
                    customer.address or 'N/A',
                ]
                if hasattr(customer, 'user') and hasattr(customer.user, 'date_joined'):
                    row.append(customer.user.date_joined.strftime('%Y-%m-%d'))
                else:
                    row.append('N/A')
                data.append(row)
            
        elif report_type == 'agents':
            queryset = Agent.objects.filter(created_at__gte=start_date, created_at__lt=end_date)
            filename = f"agents_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}"
            headers = ['ID', 'Name', 'Email', 'Mobile', 'Company', 'Location', 'Status', 'Created At']
            data = [[
                agent.agent_id,
                f"{agent.first_name} {agent.last_name}",
                agent.email,
                agent.mobile,
                agent.company,
                agent.location,
                agent.status,
                agent.created_at.strftime('%Y-%m-%d')
            ] for agent in queryset]
            
        elif report_type == 'moderators':
            queryset = Moderator.objects.all()
            if hasattr(Moderator, 'user'):
                queryset = queryset.filter(user__date_joined__gte=start_date, user__date_joined__lt=end_date)
            filename = f"moderators_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}"
            headers = ['ID', 'Name', 'Email', 'Mobile', 'Company', 'City', 'Status']
            data = []
            for moderator in queryset:
                row = [
                    moderator.moderator_id,
                    f"{moderator.first_name} {moderator.last_name}",
                    moderator.email,
                    moderator.mobile or 'N/A',
                    moderator.company or 'N/A',
                    moderator.city or 'N/A',
                    moderator.status,
                ]
                data.append(row)
            
        elif report_type == 'missing_cases':
            from ..models import MissingPerson
            queryset = MissingPerson.objects.filter(date_reported__gte=start_date, date_reported__lt=end_date)
            filename = f"missing_cases_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}"
            # Remove Age from headers as requested
            headers = ['Name', 'Gender', 'Missing From', 'Location', 'Status', 'Reported By', 'Date Reported']
            data = []
            for case in queryset:
                gender_display = dict(MissingPerson.GENDER_CHOICES).get(case.gender, 'N/A') if case.gender else 'N/A'
                status_display = dict(MissingPerson.STATUS_CHOICES).get(case.status, 'N/A') if case.status else 'N/A'
                # Ensure Missing From and Date Reported fields are properly formatted
                missing_from = case.missing_from.strftime('%Y-%m-%d') if case.missing_from else 'N/A'
                reported_date = case.date_reported.strftime('%Y-%m-%d %H:%M') if case.date_reported else 'N/A'
                
                row = [
                    f"{case.first_name} {case.last_name}",
                    # Age removed as requested
                    gender_display,
                    missing_from,  # Ensure this field is properly included
                    case.location or 'N/A',
                    status_display,
                    str(case.reported_by),
                    reported_date  # Ensure this field is properly included
                ]
                data.append(row)
            
        elif report_type == 'revenue':
            from ..models import Payment
            queryset = Payment.objects.filter(payment_date__gte=start_date, payment_date__lt=end_date, status='completed')
            filename = f"revenue_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}"
            headers = ['Payment ID', 'Booking ID', 'Amount', 'Currency', 'Payment Method', 'Payment Date']
            data = []
            for payment in queryset:
                booking_id = payment.booking.booking_id if hasattr(payment, 'booking') and payment.booking else 'N/A'
                row = [
                    payment.payment_id,
                    booking_id,
                    payment.amount,
                    payment.currency,
                    payment.payment_method,
                    payment.payment_date.strftime('%Y-%m-%d %H:%M')
                ]
                data.append(row)
        else:
            messages.error(request, "Invalid report type")
            return redirect('admin_report_gen')
        
        # Generate report file based on format
        if file_format == 'csv':
            import csv
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
            writer = csv.writer(response)
            writer.writerow(headers)
            writer.writerows(data)
            return response
            
        elif file_format == 'excel':
            import xlwt
            response = HttpResponse(content_type='application/ms-excel')
            response['Content-Disposition'] = f'attachment; filename="{filename}.xls"'
            
            wb = xlwt.Workbook(encoding='utf-8')
            ws = wb.add_sheet(report_type.capitalize())
            
            # Write header
            font_style = xlwt.XFStyle()
            font_style.font.bold = True
            for col_num, header in enumerate(headers):
                ws.write(0, col_num, header, font_style)
                
            # Write data
            for row_num, row_data in enumerate(data, 1):
                for col_num, cell_value in enumerate(row_data):
                    ws.write(row_num, col_num, str(cell_value))
                    
            wb.save(response)
            return response
            
        elif file_format == 'pdf':
            from django.template.loader import get_template
            from xhtml2pdf import pisa
            from io import BytesIO
            
            template = get_template('admin_report.html')
            context = {
                'title': f"{report_type.capitalize()} Report",
                'headers': headers,
                'data': data,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': (end_date - timedelta(days=1)).strftime('%Y-%m-%d'),
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            html = template.render(context)
            result = BytesIO()
            pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
            
            if not pdf.err:
                response = HttpResponse(result.getvalue(), content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
                return response
            
            return HttpResponse("Error generating PDF", status=400)
    
    # If not POST or any error occurred
    return redirect('admin_report_gen')

# Admin Report Preview Function
@login_required
def preview_admin_report(request):
    if not request.user.is_authenticated or request.user.user_type != 'admin':
        return JsonResponse({'status': 'error', 'message': "You don't have permission to access this page."})
        
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        report_type = request.POST.get('report_type')
        date_range_type = request.POST.get('date_range_type')
        
        # Get page number for pagination (default to 1 if not provided)
        page = int(request.POST.get('page', 1))
        page_size = 10  # Number of records per page
        
        # Initialize date variables
        start_date = None
        end_date = None
        
        # Get date range based on selection type
        if date_range_type == 'custom':
            start_date_str = request.POST.get('start_date')
            end_date_str = request.POST.get('end_date')
            if start_date_str and end_date_str:
                # Use timezone.make_aware to handle timezone warnings
                from django.utils import timezone
                start_date = timezone.make_aware(datetime.strptime(start_date_str, '%Y-%m-%d'))
                end_date = timezone.make_aware(datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1))  # Include the end date
        elif date_range_type == 'month':
            start_month_str = request.POST.get('start_month')
            end_month_str = request.POST.get('end_month')
            if start_month_str and end_month_str:
                # Use timezone.make_aware to handle timezone warnings
                from django.utils import timezone
                start_date = timezone.make_aware(datetime.strptime(f"{start_month_str}-01", '%Y-%m-%d'))
                # Calculate the end of the month
                end_month_year, end_month = map(int, end_month_str.split('-'))
                if end_month == 12:
                    next_month_year = end_month_year + 1
                    next_month = 1
                else:
                    next_month_year = end_month_year
                    next_month = end_month + 1
                end_date = timezone.make_aware(datetime.strptime(f"{next_month_year}-{next_month:02d}-01", '%Y-%m-%d'))
        
        # If dates are not properly set, return error
        if not start_date or not end_date:
            return JsonResponse({'status': 'error', 'message': "Please select valid date range"})
            
        # Format date range for display
        date_range = f"{start_date.strftime('%Y-%m-%d')} to {(end_date - timedelta(days=1)).strftime('%Y-%m-%d')}"
            
        # Generate report based on type
        if report_type == 'bookings':
            queryset = BusBooking.objects.filter(booking_date__gte=start_date, booking_date__lt=end_date)
            report_type_display = "Bus Bookings Report"
            columns = ['Booking ID', 'Customer', 'Bus', 'Seats', 'Amount', 'Booking Date', 'Payment Status']
            
            # Get total count for pagination
            total_records = queryset.count()
            total_pages = (total_records + page_size - 1) // page_size
            
            # Get paginated data
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_queryset = queryset[start_idx:end_idx]
            
            # Format data for preview
            data = []
            for booking in paginated_queryset:
                data.append({
                    'booking_id': booking.booking_id,
                    'customer': str(booking.customer),
                    'bus': str(booking.bus),
                    'seats': booking.seat_booked,
                    'amount': str(booking.total_amount),
                    'booking_date': booking.booking_date.strftime('%Y-%m-%d %H:%M'),
                    'payment_status': booking.payment_status
                })
            
        elif report_type == 'customers':
            from ..models import Customers
            queryset = Customers.objects.all()
            if hasattr(Customers, 'user'):
                queryset = queryset.filter(user__date_joined__gte=start_date, user__date_joined__lt=end_date)
            report_type_display = "Customers Report"
            columns = ['ID', 'Name', 'Email', 'Phone', 'Address', 'Joined Date']
            
            # Get total count for pagination
            total_records = queryset.count()
            total_pages = (total_records + page_size - 1) // page_size
            
            # Get paginated data
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_queryset = queryset[start_idx:end_idx]
            
            # Format data for preview
            data = []
            for customer in paginated_queryset:
                joined_date = customer.user.date_joined.strftime('%Y-%m-%d') if hasattr(customer, 'user') and hasattr(customer.user, 'date_joined') else 'N/A'
                data.append({
                    'id': customer.customer_id,
                    'name': f"{customer.first_name} {customer.last_name}",
                    'email': customer.email,
                    'phone': customer.phone or 'N/A',
                    'address': customer.address or 'N/A',
                    'joined_date': joined_date
                })
            
        elif report_type == 'agents':
            queryset = Agent.objects.filter(created_at__gte=start_date, created_at__lt=end_date)
            report_type_display = "Agents Report"
            columns = ['ID', 'Name', 'Email', 'Mobile', 'Company', 'Location', 'Status', 'Created At']
            
            # Get total count for pagination
            total_records = queryset.count()
            total_pages = (total_records + page_size - 1) // page_size
            
            # Get paginated data
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_queryset = queryset[start_idx:end_idx]
            
            # Format data for preview
            data = []
            for agent in paginated_queryset:
                data.append({
                    'id': agent.agent_id,
                    'name': f"{agent.first_name} {agent.last_name}",
                    'email': agent.email,
                    'mobile': agent.mobile,
                    'company': agent.company,
                    'location': agent.location,
                    'status': agent.status,
                    'created_at': agent.created_at.strftime('%Y-%m-%d')
                })
            
        elif report_type == 'moderators':
            queryset = Moderator.objects.all()
            if hasattr(Moderator, 'user'):
                queryset = queryset.filter(user__date_joined__gte=start_date, user__date_joined__lt=end_date)
            report_type_display = "Moderators Report"
            columns = ['ID', 'Name', 'Email', 'Mobile', 'Company', 'City', 'Status']
            
            # Get total count for pagination
            total_records = queryset.count()
            total_pages = (total_records + page_size - 1) // page_size
            
            # Get paginated data
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_queryset = queryset[start_idx:end_idx]
            
            # Format data for preview
            data = []
            for moderator in paginated_queryset:
                data.append({
                    'id': moderator.moderator_id,
                    'name': f"{moderator.first_name} {moderator.last_name}",
                    'email': moderator.email,
                    'mobile': moderator.mobile or 'N/A',
                    'company': moderator.company or 'N/A',
                    'city': moderator.city or 'N/A',
                    'status': moderator.status
                })
            
        elif report_type == 'missing_cases':
            from ..models import MissingPerson
            queryset = MissingPerson.objects.filter(date_reported__gte=start_date, date_reported__lt=end_date)
            report_type_display = "Missing Cases Report"
            # Remove Age from columns as requested
            columns = ['Name', 'Gender', 'Missing From', 'Location', 'Status', 'Reported By', 'Date Reported']
            
            # Get total count for pagination
            total_records = queryset.count()
            total_pages = (total_records + page_size - 1) // page_size
            
            # Get paginated data
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_queryset = queryset[start_idx:end_idx]
            
            # Format data for preview
            data = []
            for case in paginated_queryset:
                gender_display = dict(MissingPerson.GENDER_CHOICES).get(case.gender, 'N/A') if case.gender else 'N/A'
                status_display = dict(MissingPerson.STATUS_CHOICES).get(case.status, 'N/A') if case.status else 'N/A'
                missing_from = case.missing_from.strftime('%Y-%m-%d') if case.missing_from else 'N/A'
                reported_date = case.date_reported.strftime('%Y-%m-%d %H:%M') if case.date_reported else 'N/A'
                
                data.append({
                    'name': f"{case.first_name} {case.last_name}",
                    # Age removed as requested
                    'gender': gender_display,
                    'missing_from': missing_from,
                    'location': case.location or 'N/A',
                    'status': status_display,
                    'reported_by': str(case.reported_by),
                    'date_reported': reported_date
                })
            
        elif report_type == 'revenue':
            from ..models import Payment
            queryset = Payment.objects.filter(payment_date__gte=start_date, payment_date__lt=end_date, status='completed')
            report_type_display = "Revenue Report"
            columns = ['Payment ID', 'Booking ID', 'Amount', 'Currency', 'Payment Method', 'Payment Date']
            
            # Get total count for pagination
            total_records = queryset.count()
            total_pages = (total_records + page_size - 1) // page_size
            
            # Get paginated data
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_queryset = queryset[start_idx:end_idx]
            
            # Format data for preview
            data = []
            for payment in paginated_queryset:
                booking_id = payment.booking.booking_id if hasattr(payment, 'booking') and payment.booking else 'N/A'
                data.append({
                    'payment_id': payment.payment_id,
                    'booking_id': booking_id,
                    'amount': str(payment.amount),
                    'currency': payment.currency,
                    'payment_method': payment.payment_method,
                    'payment_date': payment.payment_date.strftime('%Y-%m-%d %H:%M')
                })
        else:
            return JsonResponse({'status': 'error', 'message': "Invalid report type"})
        
        # Return JSON response with preview data
        return JsonResponse({
            'status': 'success',
            'report_type': report_type_display,
            'columns': columns,
            'data': data,
            'date_range': date_range,
            'pagination': {
                'current_page': page,
                'total_pages': total_pages,
                'total_records': total_records,
                'page_size': page_size
            }
        })
    
    # If not AJAX POST request
    return JsonResponse({'status': 'error', 'message': "Invalid request"})