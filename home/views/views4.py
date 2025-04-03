from django.shortcuts import render,redirect
from home.models import Users
import datetime
import re
from django.contrib.auth.hashers import make_password
import face_recognition
import cv2
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.core.mail import send_mail
import random
import string
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.files.base import ContentFile
from io import BytesIO
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import numpy as np
import time
from ..models import Police
from ..models import MissingPerson
from ..models import Detected
import logging
logger = logging.getLogger(__name__)
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model  # Add this import
from home.models import Customers  # Using your existing models
from django.http import JsonResponse
account_sid = 'AC09b6c386c220d7d6cbd24145c9f22b41'
auth_token = 'aa31693c5cec3f4cbfcacf1d414ea9fe'
smsclient = Client(account_sid, auth_token)
import cv2
import numpy as np
from PIL import Image
import io
import threading
import queue
import time

def process_image(image_path, result_queue):
    try:
        # Load and resize image if needed
        img = Image.open(image_path)
        
        # Convert RGBA to RGB if needed
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        
        # Calculate new size while maintaining aspect ratio
        max_size = 1200  # Increased max size
        ratio = min(max_size/float(img.size[0]), max_size/float(img.size[1]))
        new_size = tuple([int(x*ratio) for x in img.size])
        
        # Only resize if image is larger than max_size
        if max(img.size) > max_size:
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Convert to numpy array
        img_array = np.array(img)
        
        # Try different detection methods
        face_locations = []
        
        # Method 1: Try HOG with normal parameters
        face_locations = face_recognition.face_locations(img_array, model="hog", number_of_times_to_upsample=1)
        
        # Method 2: If no face found, try CNN model (more accurate but slower)
        if not face_locations:
            try:
                face_locations = face_recognition.face_locations(img_array, model="cnn")
            except:
                pass
        
        # Method 3: If still no face, try HOG with more lenient parameters
        if not face_locations:
            face_locations = face_recognition.face_locations(img_array, model="hog", number_of_times_to_upsample=2)
        
        result_queue.put(('success', len(face_locations) > 0))
    except Exception as e:
        result_queue.put(('error', str(e)))

def process_image_with_timeout(image_path, timeout_seconds=45):  # Increased timeout
    result_queue = queue.Queue()
    processing_thread = threading.Thread(target=process_image, args=(image_path, result_queue))
    processing_thread.daemon = True
    processing_thread.start()
    
    try:
        status, result = result_queue.get(timeout=timeout_seconds)
        if status == 'error':
            raise Exception(result)
        return result
    except queue.Empty:
        raise TimeoutError("Image processing took too long")

@login_required
def userhome(request):
    try:
        # Get the customer profile for the logged-in user
        customer = Customers.objects.get(user=request.user)
        context = {
            'customer': customer,
            'user': request.user
        }
        return render(request, "userhome.html", context)
    except Customers.DoesNotExist:
        # Handle case where customer profile doesn't exist
        return redirect('welcome')  # or wherever you want to redirect

def logout(request):
    request.session.pop('user_id')
    return redirect(eg3)

def mainhome(request):
    return(render(request,"mainhome.html"))

def eg3(request):
    return(render(request,"eg3.html"))

@login_required
def alert(request):
    logger.info(f"Alert view accessed by user: {request.user.email}")
    
    try:
        # Get the police user
        police = Police.objects.get(user=request.user)
        logger.info(f"Found police profile for user: {police.policestation}")
        
        # Get all detected cases
        detected_cases = Detected.objects.all().order_by('-timestamp')
        logger.info(f"Found {detected_cases.count()} detected cases")
        
        # Prepare case data
        cases = []
        for detection in detected_cases:
            try:
                missing_person = MissingPerson.objects.get(id=detection.case_id)
                case_data = {
                    'id': detection.id,
                    'case_id': detection.case_id,
                    'name': f"{missing_person.first_name} {missing_person.last_name}",
                    'image': detection.image,
                    'timestamp': detection.timestamp
                }
                cases.append(case_data)
                logger.info(f"Added case: {case_data['name']}")
            except MissingPerson.DoesNotExist:
                logger.warning(f"Missing person not found for case_id: {detection.case_id}")
                continue
        
        context = {
            'cases': cases,
            'police': police,
            'user_id': request.user.id  # Add user_id to context
        }
        
        logger.info(f"Rendering alert.html with {len(cases)} cases")
        return render(request, "alert.html", context)
        
    except Police.DoesNotExist:
        logger.error(f"No police profile found for user: {request.user.email}")
        messages.error(request, "Access denied: Police profile not found")
        return redirect('policehome')
    except Exception as e:
        logger.error(f"Error in alert view: {str(e)}")
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('policehome')

@login_required
def discard(request):
    if request.user.user_type == 'police':
        did = request.GET['id']
        Detected.objects.get(id=did).delete()
        return redirect('alert')
    return redirect('welcome')

def aboutus(request):
    return render(request, "aboutus.html")

@login_required
def adminhome(request):
    if request.user.is_superuser:
        return render(request, "adminhome.html")
    return redirect('welcome')


@login_required
def policehome(request):
    if request.user.user_type == 'police':
        police = Police.objects.get(user=request.user)
        return render(request, "policehome2.html", {
            'user': request.user,
            'police': police
        })
    return redirect('welcome')

@login_required
def reportpolice(request):
    import logging
    logger = logging.getLogger(__name__)
    
    if request.user.user_type != 'police':
        return redirect('welcome')
    
    # Get police object for the current user at the beginning of the function
    police = None
    try:
        police = Police.objects.get(user=request.user)
    except Police.DoesNotExist:
        logger.warning(f"Police object not found for user {request.user.id}")
        pass
    
    if request.method == 'POST':
        # Import Django modules at the beginning
        from django.db import transaction
        from django.http import JsonResponse
        from django.contrib import messages
        
        # Log the POST data for debugging
        logger.info(f"POST data: {request.POST}")
        logger.info(f"FILES data: {request.FILES}")
        
        # Check if all required fields are present
        required_fields = ['first_name', 'last_name', 'dob', 'address', 'aadhar_number', 'missing_date', 'gender']
        missing_fields = [field for field in required_fields if not request.POST.get(field)]
        
        if missing_fields:
            error_msg = f"Missing required fields: {', '.join(missing_fields)}"
            logger.error(error_msg)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                })
            else:
                messages.error(request, error_msg)
                return render(request, 'report_police.html', {'police': police, 'error': error_msg})
        
        # Check if image is present
        if 'image' not in request.FILES:
            error_msg = "Missing required field: image"
            logger.error(error_msg)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                })
            else:
                messages.error(request, error_msg)
                return render(request, 'report_police.html', {'police': police, 'error': error_msg})
        
        # Get form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        date_of_birth = request.POST.get('dob')
        address = request.POST.get('address')
        aadhar_number = request.POST.get('aadhar_number')
        missing_from = request.POST.get('missing_date')
        image = request.FILES.get('image')
        gender = request.POST.get('gender')
        
        # Convert gender to model format (M/F/O)
        gender_map = {'male': 'M', 'female': 'F', 'other': 'O'}
        gender = gender_map.get(gender.lower()) if gender else None
        
        # Create MissingPerson object
        try:
            with transaction.atomic():
                person = MissingPerson(
                    first_name=first_name,
                    last_name=last_name,
                    date_of_birth=date_of_birth,
                    address=address,
                    aadhar_number=aadhar_number,
                    missing_from=missing_from,
                    image=image,
                    gender=gender,
                    reported_by=request.user,
                )
                
                # Save the person to get the image path
                person.save()
                logger.info(f"Person saved with ID: {person.id}")
                
                # Verify face in the image
                face_detected = False
                detection_method = None
                
                try:
                    # Load and preprocess the image
                    face_image = face_recognition.load_image_file(person.image.path)
                    
                    # Try multiple detection methods
                    face_locations = []
                    
                    # Method 1: Try default HOG method
                    face_locations = face_recognition.face_locations(face_image, model="hog")
                    if face_locations:
                        face_detected = True
                        detection_method = "HOG"
                    
                    if not face_detected:
                        # Method 2: Try CNN method if available
                        try:
                            face_locations = face_recognition.face_locations(face_image, model="cnn")
                            if face_locations:
                                face_detected = True
                                detection_method = "CNN"
                        except Exception as e:
                            logger.warning(f"CNN detection failed: {str(e)}")
                    
                    if not face_detected:
                        # Method 3: Try with OpenCV's Haar cascade
                        import cv2
                        img = cv2.imread(person.image.path)
                        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                        if len(faces) > 0:
                            face_locations = [(y, x + w, y + h, x) for (x, y, w, h) in faces]
                            face_detected = True
                            detection_method = "Cascade"
                    
                    # Log the detection result
                    if face_detected:
                        logger.info(f"Face detected using {detection_method} method")
                    else:
                        logger.warning("No face detected in the image")
                    
                except Exception as e:
                    logger.error(f"Face detection error: {str(e)}")
                
                # Prepare response message
                if face_detected:
                    success_msg = f"Case reported successfully! Face detected using {detection_method} method."
                else:
                    success_msg = "Case reported successfully, but the image quality might affect face detection."
                
                # Return appropriate response
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': success_msg
                    })
                else:
                    messages.success(request, success_msg)
                    return render(request, 'report_police.html', {'police': police, 'message': success_msg})
                
        except Exception as e:
            error_msg = f"Error creating missing person record: {str(e)}"
            logger.error(error_msg)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                })
            else:
                messages.error(request, error_msg)
                return render(request, 'report_police.html', {'police': police, 'error': error_msg})
    
    # GET request - render the form
    return render(request, 'report_police.html', {'police': police})

@login_required
def reportuser(request):
    if request.method == 'POST':
        try:
            # Log the received data
            logger.info(f"Received POST data: {request.POST}")
            logger.info(f"Received FILES: {request.FILES}")
            
            aadhar_number = request.POST.get('aadhar_number')
            logger.info(f"Processing aadhar number: {aadhar_number}")
            
            person = None
            try:
                person = MissingPerson.objects.get(aadhar_number=aadhar_number)
            except MissingPerson.DoesNotExist:
                pass
                
            if person:
                return JsonResponse({
                    'success': False, 
                    'error': "A person with this Aadhar number is already reported missing"
                })
                
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            date_of_birth = request.POST.get('dob')
            address = request.POST.get('address')
            missing_from = request.POST.get('missing_date')
            image = request.FILES.get('image')
            gender = request.POST.get('gender')
            location = request.POST.get('location')

            # Convert gender to model format (M/F/O)
            gender_map = {'male': 'M', 'female': 'F', 'other': 'O'}
            gender = gender_map.get(gender.lower()) if gender else None

            # Log the extracted data
            logger.info(f"Extracted data - Name: {first_name} {last_name}, DOB: {date_of_birth}, Missing from: {missing_from}")
            logger.info(f"Location selected: {location}")

            # Validate required fields
            if not all([first_name, last_name, date_of_birth, address, missing_from, image, gender, location, aadhar_number]):
                missing_fields = []
                if not first_name: missing_fields.append("First Name")
                if not last_name: missing_fields.append("Last Name")
                if not date_of_birth: missing_fields.append("Date of Birth")
                if not address: missing_fields.append("Address")
                if not missing_from: missing_fields.append("Missing Date")
                if not image: missing_fields.append("Photo")
                if not gender: missing_fields.append("Gender")
                if not location: missing_fields.append("Location")
                if not aadhar_number: missing_fields.append("Aadhar Number")
                
                error_message = f"Required fields missing: {', '.join(missing_fields)}"
                logger.error(error_message)
                return JsonResponse({'success': False, 'error': error_message})

            # Get the police station for the location
            police_station = Police.objects.filter(location=location).first()
            logger.info(f"Found police station: {police_station}")

            if police_station:
                try:
                    # Check if this is an AJAX request
                    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
                    
                    person = MissingPerson(
                        first_name=first_name,
                        last_name=last_name,
                        date_of_birth=date_of_birth,
                        address=address,
                        aadhar_number=aadhar_number,
                        missing_from=missing_from,
                        image=image,
                        gender=gender,
                        location=location,
                        reported_by=request.user,
                        investigating_police=police_station
                    )
                    
                    # Save the person first to get the image path
                    person.save()
                    
                    try:
                        # Process image with timeout to avoid hanging
                        image_path = person.image.path
                        has_face = process_image_with_timeout(image_path)
                        
                        if has_face:
                            logger.info("Face detected successfully")
                            from django.db import transaction
                            transaction.commit()
                            return JsonResponse({
                                'success': True,
                                'message': 'Case reported successfully!'
                            })
                        else:
                            # If no face is detected, delete the person and return error
                            person.delete()
                            from django.db import transaction
                            transaction.commit()
                            return JsonResponse({
                                'success': False,
                                'error': 'No face detected in the image. Please upload a clear photo showing the person\'s face.'
                            })
                            
                    except TimeoutError:
                        person.delete()
                        from django.db import transaction
                        transaction.commit()
                        return JsonResponse({
                            'success': False,
                            'error': 'Image processing took too long. Please try uploading a smaller image or contact support.'
                        })
                    except Exception as e:
                        logger.error(f"Error processing image: {str(e)}")
                        person.delete()
                        from django.db import transaction
                        transaction.commit()
                        return JsonResponse({
                            'success': False,
                            'error': 'Error processing the image. Please make sure you uploaded a valid photo file.'
                        })
                        
                except Exception as e:
                    logger.error(f"Error creating missing person record: {str(e)}")
                    return JsonResponse({
                        'success': False,
                        'error': 'Error saving the case. Please try again or contact support.'
                    })
            else:
                return JsonResponse({
                    'success': False,
                    'error': f'No police station found for location: {location}'
                })

        except Exception as e:
            logger.error(f"Unexpected error in reportuser: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'An unexpected error occurred. Please try again or contact support.'
            })

    # GET request - return the form page
    police_stations = Police.objects.values_list('location', flat=True)
    return render(request, 'report_user.html', {'police_stations': police_stations})

@login_required
def surveillance(request):
    # Get police object if user is police
    police = None
    if request.user.user_type == 'police':
        try:
            police = Police.objects.get(user=request.user)
        except Police.DoesNotExist:
            pass
            
    return render(request, "surveillance.html", {'police': police})

@login_required
def finish(request):
    case_id = request.GET["case_id"]
    obj = MissingPerson.objects.get(id=case_id)
    obj.is_finished = True
    obj.save()
    
    msg = f"""We are pleased to inform you that the missing person {obj.first_name} you were concerned about has been found. The person was located in a camera footage, and we have identified their whereabouts"""
    send_message("", msg)
    
    return redirect('policehome')

@login_required
def surveillance2(request):
    context = {
        'user_id': request.user.id,
    }
    return render(request, "surveillance2.html", context)

def send_message(to_num, msg):
    try:
        # Your Twilio account credentials
        account_sid = 'AC09b6c386c220d7d6cbd24145c9f22b41'
        auth_token = 'aa31693c5cec3f4cbfcacf1d414ea9fe'
        
        # Create a Twilio client
        client = Client(account_sid, auth_token)
        
        # Recipient phone number (with WhatsApp prefix)
        recipient = 'whatsapp:+919495064143' if not to_num else f'whatsapp:{to_num}'
        
        # Send text-only message
        message = client.messages.create(
            from_='whatsapp:+14155238886',  # Twilio's WhatsApp sandbox number
            body=msg,
            to=recipient
        )
        
        print(f"WhatsApp message sent successfully")
        print(f"Message SID: {message.sid}")
        print(f"Message Status: {message.status}")
        return True
        
    except TwilioRestException as e:
        error_code = getattr(e, 'code', 'Unknown')
        error_msg = getattr(e, 'msg', str(e))
        
        print(f"Twilio Error: Code {error_code} - {error_msg}")
        
        # Provide specific guidance based on error code
        if error_code == 20003:
            print("Authentication Error: Your Twilio auth token may be invalid or expired.")
            print("Please verify your account SID and auth token at https://www.twilio.com/console")
        elif error_code == 21608:
            print("WhatsApp Opt-in Required: The recipient has not opted in to receive messages.")
            print("Ask them to send 'join <your-sandbox-code>' to your Twilio WhatsApp number.")
        elif error_code == 21610:
            print("WhatsApp Template Error: Your message doesn't match an approved template.")
        elif error_code == 63018:
            print("Free Trial Account: You can only send messages to verified numbers.")
            
        print("\nTroubleshooting steps:")
        print("1. Verify your Twilio account is active and has sufficient funds")
        print("2. Ensure the recipient has opted in by sending 'join <your-sandbox-code>' to +14155238886")
        print("3. Check that your auth token is current at https://www.twilio.com/console")
        print("4. For sandbox usage, ensure you're following the 24-hour session rules")
        
        return False
    except Exception as e:
        print(f"Error sending WhatsApp message: {str(e)}")
        return False

@login_required
def detect(request):
    if not request.user.is_authenticated:
        messages.error(request, "Please log in to access this feature.")
        return redirect('loginn')
    
    role = request.GET.get('role')
    detected = {}
    known_images = {}
    
    try:
        # Load all missing person images and their encodings
        missing_persons = MissingPerson.objects.filter(is_finished=False)
        print(f"Found {missing_persons.count()} missing person cases")
        
        if not missing_persons.exists():
            messages.warning(request, "No missing person cases found.")
            return redirect('surveillance2' if role == 'police' else 'surveillance')
            
        # Load and process missing person images
        for person in missing_persons:
            try:
                if not person.image:
                    print(f"No image for person {person.id}")
                    continue
                    
                print(f"Loading image for person {person.id} from {person.image.path}")
                img = face_recognition.load_image_file(person.image.path)
                face_locations = face_recognition.face_locations(img)
                if not face_locations:
                    print(f"No face found in image for person {person.id}")
                    continue
                    
                face_encodings = face_recognition.face_encodings(img, face_locations)
                if face_encodings:
                    known_images[person.id] = {
                        'encoding': face_encodings[0],
                        'person': person
                    }
                    print(f"Successfully loaded face encoding for person {person.id}")
            except Exception as e:
                print(f"Error processing image for person {person.id}: {str(e)}")
                continue
        
        print(f"Loaded {len(known_images)} known faces for comparison")
        if not known_images:
            messages.warning(request, "No valid face images found in missing person cases.")
            return redirect('surveillance2' if role == 'police' else 'surveillance')
        
        known_face_encodings = [data['encoding'] for data in known_images.values()]
        known_face_ids = list(known_images.keys())
        
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            messages.error(request, "Could not access the camera.")
            return redirect('surveillance2' if role == 'police' else 'surveillance')
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame")
                continue
            
            # Resize frame for faster processing
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            
            # Scale back the face locations
            face_locations = [(top * 4, right * 4, bottom * 4, left * 4) 
                            for (top, right, bottom, left) in face_locations]
            
            for face_encoding, (top, right, bottom, left) in zip(face_encodings, face_locations):
                matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.60)
                face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                
                name = "Unknown"
                color = (0, 0, 255)  # Red for unknown faces
                matched_person = None
                
                if True in matches:
                    best_match_index = face_distances.argmin()
                    if face_distances[best_match_index] < 0.60:
                        person_id = known_face_ids[best_match_index]
                        matched_person = known_images[person_id]['person']
                        name = f"{matched_person.first_name} {matched_person.last_name}"
                        color = (0, 255, 0)  # Green for matched faces
                        
                        if person_id not in detected:
                            current_time = datetime.datetime.now()
                            detected[person_id] = current_time
                            
                            try:
                                # Save the frame as image
                                _, buffer = cv2.imencode('.jpg', frame)
                                image_file = ContentFile(
                                    buffer.tobytes(),
                                    name=f"{person_id}_{current_time.strftime('%Y%m%d_%H%M%S')}.jpg"
                                )
                                
                                # Save the detection record
                                detection = Detected.objects.create(
                                    case_id=person_id,
                                    image=image_file,
                                    timestamp=current_time.strftime("%d-%m-%Y (%I:%M %p)")
                                )
                                
                                # Send WhatsApp notification (text only)
                                msg = f"ALERT: {name} (Case ID: {person_id}) was detected on camera at {current_time.strftime('%I:%M %p, %d-%m-%Y')}"
                                send_message(None, msg)
                                print("WhatsApp notification sent")
                                
                            except Exception as e:
                                print(f"Error in detection handling: {str(e)}")
                
                # Draw the box and name for every face
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
                cv2.putText(frame, name, (left + 6, bottom - 6),
                           cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)
            
            cv2.imshow('Face Detection System', frame)
            
            # Break only if 'q' is pressed
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        # Clean up
        cap.release()
        cv2.destroyAllWindows()
        
        # Redirect to alert page if any matches were found
        if detected:
            return redirect('alert')
        return redirect('surveillance2' if role == 'police' else 'surveillance')
        
    except Exception as e:
        print(f"Error in face detection: {str(e)}")
        messages.error(request, "Error in face detection system")
        return redirect('surveillance2' if role == 'police' else 'surveillance')

# def register(request):
#     if(request.POST):
#         name=request.POST['name']
#         email=request.POST['email']
#         password=request.POST['pp']
#         phone=request.POST['phone']
#         if(Login.objects.filter(email=email)):
#             return redirect(login)
#         obj=Login(email=email,password=password,is_police=0)
#         obj.save()
#         lg_id=obj.id
#         obj2=User(login_id=lg_id,name=name,phn_num=phone)
#         obj2.save()
#     return redirect(login)

@login_required
def addpolice(request):
    if not request.user.is_superuser:
        return redirect('welcome')

    if request.method == 'POST':
        ps = request.POST.get('policestation')
        address = request.POST.get('address')
        location = request.POST.get('location')
        pn = request.POST.get('pn')
        email = request.POST.get('email')

        if get_user_model().objects.filter(email=email).exists():
            # Get statistics for the page
            police_station_count = Police.objects.count()
            active_cases_count = MissingPerson.objects.filter(is_finished=False).count()
            surveillance_alerts = Detected.objects.count()
            user_count = Users.objects.count()
            
            return render(request, "addpolice.html", {
                "error": "Email already exists",
                "police_station_count": police_station_count,
                "active_cases_count": active_cases_count,
                "surveillance_alerts": surveillance_alerts,
                "user_count": user_count
            })

        password = generate_random_password()
        try:
            # Create User account
            user = get_user_model().objects.create_user(
                username=email,
                email=email,
                password=password,
                user_type='police',
                is_police=True
            )

            # Create Police profile
            Police.objects.create(
                user=user,
                policestation=ps,
                address=address,
                location=location,
                phnnum=pn
            )

            # Send email with credentials
            subject = 'Your Police Account Credentials'
            message = f'''Hello,

Your police account has been created. Here are your login credentials:

Email: {email}
Password: {password}

Please change your password after first login.

Best regards,
FaceTrace Pro Team'''

            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            messages.success(request, "Police account created and credentials sent via email")
            return redirect('viewpolice')

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

    # Get statistics for the page
    police_station_count = Police.objects.count()
    active_cases_count = MissingPerson.objects.filter(is_finished=False).count()
    surveillance_alerts = Detected.objects.count()
    user_count = Users.objects.count()
    
    return render(request, "addpolice.html", {
        "police_station_count": police_station_count,
        "active_cases_count": active_cases_count,
        "surveillance_alerts": surveillance_alerts,
        "user_count": user_count
    })

def generate_random_password():
    """Generate a random password"""
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for i in range(12))

def send_registration_email(user, password):
    """Send registration email to the police station."""
    subject = 'Registration Confirmation - FaceTrace Pro'
    message = f'''Hello,

Your account has been successfully registered with FaceTrace Pro.

Login Credentials:
Username/Email: {user.email}
Password: {password}

Please keep these credentials secure and change your password after first login.

Best regards,
The FaceTrace Pro Team'''
    
    try:
        send_mail(
            subject,
            message,
            'amaltomy321@gmail.com',  # From email
            [user.email],  # To email
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        print(f"Error Type: {type(e).__name__}")
        return False

@login_required
def viewpolice(request):
    if not request.user.is_superuser:
        return redirect('welcome')
        
    police_details = Police.objects.select_related('user').all()
    data = [
        {
            'id': police.id,
            'policestation': police.policestation,
            'address': police.address,
            'location': police.location,
            'phnnum': police.phnnum,
            'email': police.user.email
        }
        for police in police_details
    ]
    return render(request, "viewpolice.html", {"police_details": data})

@login_required
def viewuser(request):
    if not request.user.is_superuser:
        return redirect('welcome')
        
    users = get_user_model().objects.all()
    data = [
        {
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'phone': user.customers.phone if hasattr(user, 'customers') else None
        }
        for user in users
    ]
    return render(request, "viewuser.html", {"user_details": data})

def get_phone_number(user_id, is_police):
    try:
        if is_police:
            police = Police.objects.get(user_id=user_id)
            return police.phnnum
        else:
            user = get_user_model().objects.get(id=user_id)
            return user.customers.phone if hasattr(user, 'customers') else None
    except (Police.DoesNotExist, get_user_model().DoesNotExist):
        return None

@login_required
def missing(request):
    search_query = request.GET.get('search', '')
    persons = MissingPerson.objects.filter(is_finished=False)
    
    if search_query:
        persons = persons.filter(aadhar_number=search_query)
        
    personobj = []
    for person in persons:
        # Get reporter's phone number
        if person.reported_by.user_type == 'police':
            reported_by_phone = Police.objects.get(user=person.reported_by).phnnum
        else:
            reported_by_phone = person.reported_by.customers.phone if hasattr(person.reported_by, 'customers') else None
        
        # Get investigating police phone number directly from the Police object
        police_station_phone = person.investigating_police.phnnum if person.investigating_police else None
        
        personobj.append({
            'person': person,
            'reported_by_phone': reported_by_phone,
            'police_station_phone': police_station_phone
        })
    
    return render(request, "missing.html", {
        "missingperson": personobj,
        "search_query": search_query
    })

@login_required
def missing2(request):
    search_query = request.GET.get('search', '')
    persons = MissingPerson.objects.filter(is_finished=False)
    
    if search_query:
        persons = persons.filter(aadhar_number__icontains=search_query)
    
    for person in persons:
        if person.reported_by.user_type == 'police':
            person.phone = Police.objects.get(user=person.reported_by).phnnum
        else:
            person.phone = person.reported_by.customers.phone if hasattr(person.reported_by, 'customers') else None
    
    # Get police object if user is police
    police = None
    if request.user.user_type == 'police':
        try:
            police = Police.objects.get(user=request.user)
        except Police.DoesNotExist:
            pass
    
    return render(request, "missing2.html", {
        "missingperson": persons,
        "search_query": search_query,
        "police": police
    })

@login_required
def missing3(request):
    search_query = request.GET.get('search', '')
    persons = MissingPerson.objects.filter(is_finished=False)
    
    if search_query:
        persons = persons.filter(aadhar_number=search_query)
    
    personobj = []
    for person in persons:
        reported_by_phone = get_phone_number(person.reported_by.id, is_police=False)
        police_station_phone = get_phone_number(person.investigating_police.id, is_police=True)
        
        personobj.append({
            'person': person,
            'reported_by_phone': reported_by_phone,
            'police_station_phone': police_station_phone
        })
    
    # Get police object if user is police
    police = None
    if request.user.user_type == 'police':
        try:
            police = Police.objects.get(user=request.user)
        except Police.DoesNotExist:
            pass
    
    return render(request, "missing3.html", {
        "missingperson": personobj,
        "search_query": search_query,
        "police": police
    })

@login_required
def viewcase(request):
    user_id = request.user.id
    search_query = request.GET.get('search', '')
    persons = MissingPerson.objects.filter(reported_by=user_id)
    
    for person in persons:
        try:
            if person.reported_by.user_type == 'police':
                person.phone = Police.objects.get(user=person.reported_by).phnnum
            else:
                # Get phone from customer profile
                customer = Customers.objects.get(user=person.reported_by)
                person.phone = customer.phone
        except (Police.DoesNotExist, Customers.DoesNotExist):
            person.phone = None
    
    if search_query:
        persons = persons.filter(aadhar_number__icontains=search_query)
    
    return render(request, 'viewcase.html', {
        'missingperson': persons,
        'search_query': search_query,
        'user_id': user_id
    })

@login_required
def viewcase2(request):
    user_id = request.user.id
    search_query = request.GET.get('search', '')
    persons = MissingPerson.objects.filter(reported_by=user_id)
    
    for person in persons:
        if person.reported_by.user_type == 'police':
            person.phone = Police.objects.get(user=person.reported_by).phnnum
        else:
            person.phone = person.reported_by.customers.phone if hasattr(person.reported_by, 'customers') else None
    
    if search_query:
        persons = persons.filter(aadhar_number__icontains=search_query)
    
    # Get police object if user is police
    police = None
    if request.user.user_type == 'police':
        try:
            police = Police.objects.get(user=request.user)
        except Police.DoesNotExist:
            pass
    
    return render(request, 'viewcase2.html', {
        'missingperson': persons,
        'search_query': search_query,
        'police': police
    })

@login_required
def investigatingcase(request):
    if request.user.user_type == 'police':
        try:
            # Get the police object using the logged-in user
            police = Police.objects.get(user=request.user)
            
            # Get the search query from the request
            search_query = request.GET.get('search', '')
            
            # Get all cases being investigated by this police officer
            cases = MissingPerson.objects.filter(investigating_police=police)
            
            # If there's a search query, filter by Aadhar number
            if search_query:
                cases = cases.filter(aadhar_number__icontains=search_query)
            
            return render(request, "investigatingcase.html", {
                "cases": cases,
                "police": police,
                "search_query": search_query
            })
            
        except Police.DoesNotExist:
            messages.error(request, "Police profile not found")
            return redirect('policehome')
    
    return redirect('welcome')

@login_required
def transfercase(request):
    case_id = request.GET.get('caseid')
    if request.method == 'POST':
        police_location = request.POST.get('station')
        obj = MissingPerson.objects.get(id=case_id)
        p = Police.objects.get(location=police_location)
        obj.investigating_police = p.user
        obj.save()
        return redirect('investigatingcase')
    
    police_stations = Police.objects.values_list('location', flat=True)
    return render(request, "transfercase.html", {"locations": police_stations})

@login_required
def deletepolice(request):
    if not request.user.is_superuser:
        return redirect('welcome')
    
    police_id = request.GET.get('id')
    try:
        obj = Police.objects.get(id=police_id)
        obj.delete()
        messages.success(request, "Police officer deleted successfully.")
    except Police.DoesNotExist:
        messages.error(request, "Police officer not found.")
    
    return redirect('viewpolice')

@login_required
def deleteuser(request):
    if not request.user.is_superuser:
        return redirect('welcome')
    
    user_id = request.GET.get('id')
    try:
        user = get_user_model().objects.get(id=user_id)
        user.delete()
        messages.success(request, "User deleted successfully.")
    except get_user_model().DoesNotExist:
        messages.error(request, "User not found.")
    
    return redirect('viewuser')

@login_required
def deleteperson(request):
    person_id = request.GET.get('id')
    is_p = request.GET.get('is_p', 'False')  # Default to 'False' if not provided
    
    try:
        MissingPerson.objects.get(id=person_id).delete()
        messages.success(request, "Missing person record deleted successfully.")
    except MissingPerson.DoesNotExist:
        messages.error(request, "Missing person record not found.")
    
    if request.user.is_superuser:
        return redirect('missing3')
    elif is_p == 'True':
        return redirect('viewcase2')
    else:
        return redirect('userhome')

@login_required
def edituser(request):
    if not request.user.is_superuser:
        return redirect('welcome')
    
    if request.method == 'POST':
        users_id = request.POST.get('p_id')
        name = request.POST.get('name')
        pn = request.POST.get('password')
        email = request.POST.get('email')
        
        try:
            user = get_user_model().objects.get(id=users_id)
            user.first_name = name
            user.email = email
            user.set_password(pn)  # Use set_password to hash the password
            user.save()
            messages.success(request, "User updated successfully.")
        except get_user_model().DoesNotExist:
            messages.error(request, "User not found.")
        
        return redirect('viewuser')
    
    users_id = request.GET.get('id')
    try:
        user = get_user_model().objects.get(id=users_id)
    except get_user_model().DoesNotExist:
        messages.error(request, "User not found.")
        return redirect('viewuser')
    
    return render(request, "edituser.html", {"user": user})

@login_required
def editpolice(request):
    if not request.user.is_superuser:
        return redirect('welcome')
    
    if request.method == 'POST':
        police_id = request.POST.get('p_id')
        ps = request.POST.get('policestation')
        address = request.POST.get('address')
        location = request.POST.get('location')
        pn = request.POST.get('pn')
        email = request.POST.get('email')
        
        try:
            police = Police.objects.get(id=police_id)
            police.policestation = ps
            police.address = address
            police.location = location
            police.phnnum = pn
            police.user.email = email
            police.user.save()
            police.save()
            messages.success(request, "Police officer updated successfully.")
        except Police.DoesNotExist:
            messages.error(request, "Police officer not found.")
        
        return redirect('viewpolice')
    
    police_id = request.GET.get('id')
    try:
        police = Police.objects.get(id=police_id)
    except Police.DoesNotExist:
        messages.error(request, "Police officer not found.")
        return redirect('viewpolice')
    
    return render(request, "editpolicestation.html", {"police": police})

@login_required
def editperson(request):
    if request.method == 'POST':
        person_id = request.POST.get('p_id')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        date_of_birth = request.POST.get('dob')
        address = request.POST.get('address')
        gender = request.POST.get('gender')
        
        try:
            obj = MissingPerson.objects.get(id=person_id)
            obj.first_name = first_name
            obj.last_name = last_name
            obj.date_of_birth = date_of_birth
            obj.address = address
            obj.gender = gender
            obj.save()
            messages.success(request, "Missing person record updated successfully.")
        except MissingPerson.DoesNotExist:
            messages.error(request, "Missing person record not found.")
        
        return redirect('viewcase')
    
    person_id = request.GET.get('id')
    try:
        obj = MissingPerson.objects.get(id=person_id)
    except MissingPerson.DoesNotExist:
        messages.error(request, "Missing person record not found.")
        return redirect('viewcase')
    
    person = {
        "id": obj.id,
        "first_name": obj.first_name,
        "last_name": obj.last_name,
        "date_of_birth": obj.date_of_birth,
        "address": obj.address,
        "gender": obj.gender
    }
    return render(request, "editperson.html", {"person": person})

@login_required
def test_whatsapp(request):
    try:
        # Get the phone number from the URL parameter
        phone = request.GET.get('phone', '')
        if not phone:
            messages.error(request, "Please provide a phone number")
            return redirect('policehome')
            
        # Send a test message
        msg = "This is a test message from FaceTracePro"
        success = send_message(phone, msg)
        
        if success:
            messages.success(request, f"Test message sent successfully to {phone}")
        else:
            messages.error(request, f"Failed to send test message to {phone}")
            
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
    
    return redirect('policehome')

def create_police_user(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        # ... other fields ...
        
        # Generate random password
        password = generate_random_password()
        
        # Create user
        user = Users.objects.create_user(
            username=email,
            email=email,
            password=password,
            user_type='police',
            is_police=True
        )
        
        # Create police profile
        police = Police.objects.create(
            user=user,
            policestation=request.POST.get('policestation'),
            # ... other fields ...
        )
        
        # Send email with credentials
        subject = 'Your Police Account Credentials'
        message = f'''
        Hello,
        
        Your police account has been created. Here are your login credentials:
        
        Email: {email}
        Password: {password}
        
        Please change your password after first login.
        
        Best regards,
        Your System
        '''
        
        try:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            messages.success(request, "Police account created and credentials sent via email")
        except Exception as e:
            messages.error(request, f"Account created but failed to send email: {str(e)}")
        
        return redirect('admin_dashboard')  # or wherever you want to redirect
