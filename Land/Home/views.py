from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.db import transaction as db_transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy

from .models import Customer, SubRegistrar, SubRegistrarOffice, Transaction, assign_group
from .utils import predictor  # assuming existing module
from django.http import JsonResponse


def index(request):
    return render(request, 'index.html')

def customer_register(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        adhar_no = request.POST.get('aadhar_number', '').strip()
        phone_no = request.POST.get('phone', '').strip()
        date_of_birth = request.POST.get('date_of_birth', '').strip()
        pan_number = request.POST.get('pan_number', '').strip()
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        state = request.POST.get('state', '').strip()
        pincode = request.POST.get('pincode', '').strip()

        # validations
        if not all([full_name, email, password, confirm_password, adhar_no, phone_no, date_of_birth, pan_number, address, city, state, pincode]):
            messages.error(request, "All fields are required.")
            return render(request, 'auth/register.html')

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return render(request, 'auth/register.html')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'auth/register.html')

        if not (len(adhar_no) == 12 and adhar_no.isdigit()):
            messages.error(request, "Aadhaar number must be exactly 12 digits.")
            return render(request, 'auth/register.html')

        pan_u = pan_number.upper()
        if not (len(pan_u) == 10 and pan_u.isalnum()):
            messages.error(request, "PAN must be 10 alphanumeric characters.")
            return render(request, 'auth/register.html')

        if not (len(pincode) == 6 and pincode.isdigit()):
            messages.error(request, "PIN code must be exactly 6 digits.")
            return render(request, 'auth/register.html')

        if User.objects.filter(username=email).exists():
            messages.error(request, "An account with this email already exists.")
            return render(request, 'auth/register.html')

        if Customer.objects.filter(adhar_no=adhar_no).exists():
            messages.error(request, "This Aadhaar number is already registered.")
            return render(request, 'auth/register.html')

        if Customer.objects.filter(phone_no=phone_no).exists():
            messages.error(request, "This phone number is already registered.")
            return render(request, 'auth/register.html')

        if Customer.objects.filter(email=email).exists():
            messages.error(request, "This email is already registered.")
            return render(request, 'auth/register.html')

        try:
            first_name, last_name = (full_name.split(' ', 1) + [''])[:2]
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            assign_group(user, "Resident")
            Customer.objects.create(
                user=user,
                adhar_no=adhar_no,
                phone_no=phone_no,
                date_of_birth=date_of_birth,
                pan_number=pan_u,
                address=address,
                city=city,
                state=state,
                pincode=pincode,
                email=email
            )
            messages.success(request, f"Welcome {full_name}! Account created successfully.")
            return redirect('customer_login')
        except Exception as e:
            messages.error(request, "An error occurred while creating your account.")
            return render(request, 'auth/register.html')

    return render(request, 'auth/register.html')

def customer_login(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            try:
                customer = Customer.objects.get(user=user)
                login(request, user)
                request.session['customer_id'] = customer.id
                request.session['customer_name'] = f"{user.first_name} {user.last_name}".strip()
                messages.success(request, f"Welcome {request.session['customer_name']}!")
                return redirect('customer_dashboard')
            except Customer.DoesNotExist:
                messages.error(request, "User exists but no Customer profile found.")
        else:
            messages.error(request, "Invalid email or password.")
    return render(request, 'auth/login.html')

def customer_logout(request):
    auth_logout(request)
    messages.success(request, "Logged out.")
    return redirect('customer_login')

def registrar_login(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            try:
                SubRegistrar.objects.get(user=user)
                login(request, user)
                request.session['subregistrar_name'] = f"{user.first_name} {user.last_name}".strip()
                messages.success(request, f"Welcome {request.session['subregistrar_name']}!")
                return redirect('registrar_dashboard')
            except SubRegistrar.DoesNotExist:
                messages.error(request, "User exists but no Sub-Registrar profile found.")
        else:
            messages.error(request, "Invalid username or password.")
    return render(request, 'auth/registrar_login.html')

@login_required
def customer_dashboard(request):
    customer = get_object_or_404(Customer, user=request.user)
    stats = {
        'pending_transactions': customer.transactions.filter(status='pending').count(),
        'under_review_transactions': customer.transactions.filter(status='pending').count(),
        'approved_transactions': customer.transactions.filter(status='approved').count(),
        'notifications_count': 5,
        'total_transactions': customer.transactions.count(),
    }
    recent_activities = [
        {'action': 'Transaction Approved', 'description': 'Sale deed approved', 'timestamp': 'Just now', 'icon': 'fas fa-check', 'color': 'green'},
        {'action': 'Document Under Review', 'description': 'Will deed in review', 'timestamp': '1 day ago', 'icon': 'fas fa-search', 'color': 'blue'},
        {'action': 'Document Uploaded', 'description': 'Inheritance deed uploaded', 'timestamp': '3 days ago', 'icon': 'fas fa-upload', 'color': 'yellow'},
    ]
    context = {'customer': customer, 'stats': stats, 'recent_activities': recent_activities}
    return render(request, 'auth/customer_dashboard.html', context)

def is_superuser(user):
    return user.is_superuser



# ✅ Access control: allow superuser or linked SubRegistrar
def is_admin_user(user):
    return user.is_superuser or SubRegistrar.objects.filter(user=user).exists()

def admin_dashboard(request):
    # Fetch all SubRegistrars with related office and user details
    subregistrars = SubRegistrar.objects.select_related('user', 'office').all()

    context = {
        'total_customers': Customer.objects.count(),
        'total_registrars': subregistrars.count(),
        'pending_transactions': Transaction.objects.filter(status='pending').count(),
        'blockchain_uptime': 99.8,
        'system_alerts': [
            {
                'type': 'red',
                'icon': 'exclamation-triangle',
                'title': 'High pending volume',
                'description': 'Pending transactions waiting for approval',
                'timestamp': '5 min ago',
            },
            {
                'type': 'yellow',
                'icon': 'exclamation-circle',
                'title': 'Blockchain sync delay',
                'description': 'Transactions pending chain confirmation',
                'timestamp': '15 min ago',
            },
        ],
        'subregistrars': subregistrars,  # ✅ Pass to template
    }

    return render(request, 'auth/admin_dashboard.html', context)


@login_required
@user_passes_test(is_admin_user, login_url='/no-access')
def edit_subregistrar(request, pk):
    sub = get_object_or_404(SubRegistrar, pk=pk)
    offices = SubRegistrarOffice.objects.all()

    if request.method == 'POST':
        office_id = request.POST.get('office')
        sub.office = get_object_or_404(SubRegistrarOffice, pk=office_id)
        sub.contact_number = request.POST.get('contact_number')
        sub.email = request.POST.get('email')
        sub.status = request.POST.get('status')
        sub.save()
        return redirect('admin_dashboard')

    return render(request, 'auth/edit_subregistrar.html', {'sub': sub, 'offices': offices})


@login_required
@user_passes_test(is_admin_user, login_url='/no-access')
def delete_subregistrar(request, pk):
    sub = get_object_or_404(SubRegistrar, pk=pk)

    if request.method == 'POST':
        sub.delete()
        return redirect('admin_dashboard')

    return render(request, 'auth/confirm_delete.html', {'sub': sub})


@login_required
@user_passes_test(is_superuser, login_url='/')
def admin_user_management(request):
    context = {
        'recent_users': [
            {'name': 'Rajesh Kumar', 'email': 'rajesh@kerala.gov.in', 'role': 'Registrar', 'region': 'Kochi', 'last_login': '2 hours ago', 'status': 'Active'}
        ]
    }
    return render(request, 'admin/user_management.html', context)

@login_required
@user_passes_test(is_superuser, login_url='/')
def admin_system_config(request):
    context = {
        'transaction_types': [
            {'name': 'Sale Deed', 'enabled': True},
            {'name': 'Gift Deed', 'enabled': True},
            {'name': 'Will', 'enabled': True},
        ],
        'system_settings': {'email_notifications': True, 'sms_alerts': False, 'auto_archive': True}
    }
    return render(request, 'admin/system_config.html', context)

@login_required
@user_passes_test(is_superuser, login_url='/')
def admin_blockchain_management(request):
    context = {
        'network_status': {'health': 'Excellent', 'last_block': '#2,547,891', 'confirmation_time': '~15 seconds', 'gas_price': '0.002 ETH'},
        'pending_anchoring': [
            {'tx_id': 'TX2025045', 'type': 'Sale deed', 'status': 'Pending', 'description': 'Awaiting blockchain confirmation'},
            {'tx_id': 'TX2025044', 'type': 'Gift deed', 'status': 'Failed', 'description': 'Failed to anchor - network congestion'},
        ]
    }
    return render(request, 'admin/blockchain_management.html', context)

@login_required
@user_passes_test(is_superuser, login_url='/')
def admin_data_management(request):
    context = {'storage_stats': {'total_storage': '2.4 TB', 'documents_stored': 45234, 'active_records': 12890, 'archived_records': 32344}}
    return render(request, 'admin/data_management.html', context)

@login_required
@user_passes_test(is_superuser, login_url='/')
def admin_analytics(request):
    context = {'realtime_metrics': {'active_sessions': 847, 'success_rate': 98.7, 'avg_response': '156ms', 'uptime': 99.9}}
    return render(request, 'admin/analytics.html', context)

@login_required
@user_passes_test(is_superuser, login_url='/')
def admin_reports(request):
    context = {'recent_reports': [{'name': 'Monthly Transaction Report - Jan 2025', 'type': 'Compliance', 'generated': 'Jan 30, 2025', 'size': '2.4 MB'}]}
    return render(request, 'admin/reports.html', context)

@login_required
@user_passes_test(is_superuser, login_url='/')
def admin_security(request):
    context = {
        'security_status': {'encryption': 'Active', 'access_control': 'Enforced', 'audit_logging': 'Enabled'},
        'suspicious_activities': [
            {'title': 'Multiple Failed Login Attempts', 'description': 'User: admin@example.com - 5 failed attempts', 'severity': 'Medium', 'timestamp': '30 minutes ago'},
            {'title': 'Unusual Access Pattern', 'description': 'Registrar accessing from new location', 'severity': 'High', 'timestamp': '2 hours ago'},
        ]
    }
    return render(request, 'admin/security.html', context)

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction as db_transaction
from django.contrib.auth.models import User

@login_required
@user_passes_test(lambda u: u.is_superuser, login_url='/')
def create_subregistrar(request):
    """
    Create a Sub-Registrar with full details: username, password, office, contact, email, status.
    """
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        office_id = request.POST.get('office_id', '').strip()
        contact_number = request.POST.get('contact_number', '').strip()
        email = request.POST.get('email', '').strip()
        status = request.POST.get('status', 'active').strip()  # default to 'active'

        # Validate required fields
        if not all([username, password, confirm_password, office_id]):
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'auth/subregistrarcreation.html', get_form_context())

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'auth/subregistrarcreation.html', get_form_context())

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return render(request, 'auth/subregistrarcreation.html', get_form_context())

        if User.objects.filter(username=username).exists():
            messages.error(request, "A user with this username already exists.")
            return render(request, 'auth/subregistrarcreation.html', get_form_context())

        office = get_object_or_404(SubRegistrarOffice, pk=office_id)

        try:
            with db_transaction.atomic():
                # Create the user
                user = User.objects.create_user(username=username, password=password, email=email)
                
                # Create the subregistrar profile
                subregistrar = SubRegistrar.objects.create(
                    user=user,
                    office=office,
                    contact_number=contact_number,
                    email=email,
                    status=status
                )

                messages.success(
                    request,
                    f"Sub-Registrar '{username}' created for {office.district}, {office.locality}."
                )
                return redirect('registrar_login')
        except Exception as e:
            messages.error(request, f"Error creating sub-registrar account: {str(e)}")
            return render(request, 'auth/subregistrarcreation.html', get_form_context())

    # GET request
    return render(request, 'auth/subregistrarcreation.html', get_form_context())

import json
from django.core.serializers.json import DjangoJSONEncoder

def get_form_context():
    offices = SubRegistrarOffice.objects.all()
    districts = sorted(set((o.district, o.district) for o in offices))
    context = {
        "offices": offices,
        "districts": districts,
        "offices_json": json.dumps([{"id": o.id, "district": o.district, "locality": o.locality} for o in offices], cls=DjangoJSONEncoder),
    }
    return context

from django.db.models import Q
from django.utils import timezone

@login_required
def registrar_dashboard(request):
    subregistrar = get_object_or_404(SubRegistrar, user=request.user)

    # Transactions belonging to this sub-registrar's office
    applications = Transaction.objects.filter(office=subregistrar.office)

    # Optional: apply filters from GET params
    deed_type = request.GET.get('deed_type')
    if deed_type:
        applications = applications.filter(deed_type=deed_type)

    from_date = request.GET.get('from_date')
    if from_date:
        applications = applications.filter(submission_date__date__gte=from_date)

    to_date = request.GET.get('to_date')
    if to_date:
        applications = applications.filter(submission_date__date__lte=to_date)

    customer_name = request.GET.get('customer_name')
    if customer_name:
        applications = applications.filter(
            Q(customer__user__first_name__icontains=customer_name) |
            Q(customer__user__last_name__icontains=customer_name)
        )

    stats = {
        'pending_transactions': applications.filter(status='pending').count(),
        'under_review_transactions': applications.filter(status='under_review').count(),
        'approved_transactions': applications.filter(status='approved').count(),
        'notifications_count': 4,
        'total_transactions': applications.count(),
    }

    recent_activities = [
        {'action': 'Transaction Approved', 'description': 'Sale deed approved', 'timestamp': 'Just now', 'icon': 'fas fa-check', 'color': 'green'},
        {'action': 'Document Under Review', 'description': 'Gift deed under review', 'timestamp': '2 days ago', 'icon': 'fas fa-search', 'color': 'blue'},
        {'action': 'Document Uploaded', 'description': 'Will deed uploaded', 'timestamp': '4 days ago', 'icon': 'fas fa-upload', 'color': 'yellow'},
    ]

    context = {
        'registrar': subregistrar,
        'stats': stats,
        'recent_activities': recent_activities,
        'applications': applications.order_by('-submission_date'),  # <-- pass to template
        'today_date': timezone.now().date(),
    }

    return render(request, 'auth/registrar_dashboard.html', context)




def get_form_context():
    """Prepare context for create_subregistrar form"""
    offices = SubRegistrarOffice.objects.all().order_by('district', 'locality')
    
    # Unique districts for dropdown
    districts = sorted(set((office.district, office.district) for office in offices))
    
    # JSON for dynamic office filtering in JS
    offices_json = json.dumps(
        [{"id": o.id, "district": o.district, "locality": o.locality} for o in offices],
        cls=DjangoJSONEncoder
    )
    
    return {
        "offices": offices,
        "districts": districts,
        "offices_json": offices_json
    }


@login_required
def submit_transaction(request):
    customer = get_object_or_404(Customer, user=request.user)
    offices = SubRegistrarOffice.objects.all().order_by('district', 'locality')

    if request.method == "POST":
        deed_type = request.POST.get('deed_type', '').strip()
        survey_no = request.POST.get('survey_no', '').strip()
        location = request.POST.get('location', '').strip()
        valuation_raw = request.POST.get('property_valuation', '').strip()
        party_name = request.POST.get('party_name', '').strip()
        party_contact = request.POST.get('party_contact', '').strip()
        party_id = request.POST.get('party_id', '').strip()
        office_id = request.POST.get('office_id', '').strip()
        documents = request.FILES.getlist('documents')

        if not all([deed_type, survey_no, location, valuation_raw, party_name, party_contact, party_id, office_id]) or len(documents) == 0:
            messages.error(request, "Please fill all required fields and select an office, and upload at least one document.")
            return render(request, "customer/submit.html", {'customer': customer, 'offices': offices})

        try:
            valuation = Decimal(valuation_raw)
        except (InvalidOperation, TypeError):
            messages.error(request, "Invalid valuation amount.")
            return render(request, "customer/submit.html", {'customer': customer, 'offices': offices})

        office = get_object_or_404(SubRegistrarOffice, pk=office_id)

        saved_files = []
        for doc in documents:
            path = default_storage.save(f'transactions/{customer.id}/{doc.name}', doc)
            saved_files.append(path)

        tx = Transaction.objects.create(
         customer=customer,
        deed_type=deed_type,
        survey_number=survey_no,
        location=location,
        valuation=valuation,
        party_name=party_name,
        party_contact=party_contact,
        party_id=party_id,
        office=office,   # <-- Use the selected office
        status='pending',
        documents=saved_files


)


        messages.success(request, "Transaction submitted to the selected office, awaiting sub-registrar review.")
        return redirect('customer_dashboard')

    return render(request, "customer/submit.html", {'customer': customer, 'offices': offices})


@login_required
def transaction_wallet(request):
    customer = get_object_or_404(Customer, user=request.user)
    return render(request, 'dashboard/transaction_wallet.html', {'customer': customer})

@login_required
def verify_certificate(request):
    customer = get_object_or_404(Customer, user=request.user)
    return render(request, 'dashboard/verify_certificate.html', {'customer': customer})

@login_required
def property_valuation(request):
    districts = predictor.get_districts()
    if request.method == 'POST':
        district = request.POST.get('district', '')
        locality = request.POST.get('locality', '')
        try:
            result = predictor.predict_price(district, locality)
            return render(request, 'prediction.html', {'districts': districts, 'result': result})
        except Exception as e:
            return render(request, 'prediction.html', {'districts': districts, 'error': str(e)})
    return render(request, 'prediction.html', {'districts': districts})

def get_localities_ajax(request):
    district = request.GET.get('district', '')
    localities = predictor.get_localities(district)
    return JsonResponse({'localities': localities})

def list_subregistrars(request):
    offices = SubRegistrarOffice.objects.all()
    return render(request, "admin/subregistrar_offices.html", {"subregistrars": offices})

# views.py
from django.shortcuts import render
from django.utils.timezone import datetime
from .models import Transaction

@login_required
def applications_list(request):
    applications = Transaction.objects.all().select_related("customer", "office")

    # Filters
    deed_type = request.GET.get("deed_type")
    from_date = request.GET.get("from_date")
    to_date = request.GET.get("to_date")
    customer_name = request.GET.get("customer_name")

    if deed_type:
        applications = applications.filter(deed_type=deed_type)

    if from_date:
        applications = applications.filter(submission_date__date__gte=from_date)

    if to_date:
        applications = applications.filter(submission_date__date__lte=to_date)

    if customer_name:
        applications = applications.filter(customer__user__first_name__icontains=customer_name) | applications.filter(customer__user__last_name__icontains=customer_name)

    applications = applications.order_by("-submission_date")

    return render(request, "subregistrar/applications_list.html", {
        "applications": applications,
        "today_date": datetime.today().date()
    })
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from .models import Transaction, SubRegistrar

@login_required
def application_detail(request, pk):
    """
    Display all details for a single transaction for the registrar.
    """
    # Ensure the logged-in user is a sub-registrar
    subregistrar = get_object_or_404(SubRegistrar, user=request.user)

    # Fetch the transaction and ensure it belongs to the sub-registrar's office
    application = get_object_or_404(Transaction, pk=pk, office=subregistrar.office)

    context = {
        "application": application,
        "customer_name": application.customer.user.get_full_name(),
        "deed_type_display": application.get_deed_type_display(),
        "survey_number": application.survey_number,
        "location": application.location,
        "valuation": application.valuation,
        "party_name": application.party_name,
        "party_contact": application.party_contact,
        "party_id": application.party_id,
        "submission_date": application.submission_date,
        "status": application.status,
        "rejection_reason": application.rejection_reason,
        "documents": application.documents,
    }
    return render(request, "customer/detail.html", context)
