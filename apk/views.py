from django.http import HttpResponse
from django.shortcuts import render,redirect
from .models import registration,Staff,acdet,branch,temp_daybook
from django import forms
from .forms import StaffForm
from django.contrib import messages
from django.contrib.auth import logout
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime
from datetime import date
from django.utils.timezone import now
from django.db.models import OuterRef, Subquery, Min

def user_login(request):
    if request.method == 'POST':
        Username = request.POST.get('Username')
        Password = request.POST.get('Password')
        user = registration.objects.filter(Username=Username, Password=Password).first()

        if user:
            if user.Status == "Opened":
                return redirect('index', user_id=user.id)
            else:
                messages.error(request, 'Invalid User!!')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

def index(request, user_id):
    user = registration.objects.filter(id=user_id).first()
    return render(request, 'index.html', {'user': user})

def user_reg(request, user_id):
    user = registration.objects.filter(id=user_id).first()

    if not user:
        return redirect('login')

    if user.B_id.Branch_name == "Head Office":
        branch_list = branch.objects.filter(active="y")
        user_data = registration.objects.all().order_by('Username')  
    else:
        branch_list = branch.objects.filter(Branch_name=user.B_id.Branch_name)
        user_data = registration.objects.filter(B_id__Branch_name=user.B_id.Branch_name).order_by('Username')

    if request.method == 'POST':
        username = request.POST.get('Username')
        password = request.POST.get('Password')
        branch_code = request.POST.get('Branch_code', '')
        user_level = request.POST.get('User_level')
        status = request.POST.get('Status')

        branch_obj = branch.objects.filter(Branch_code=branch_code).first()

        if not branch_obj:
            messages.error(request, "Invalid Branch Code.")
            return redirect(f'/user_reg/{user.id}?error=invalid_branch')

        existing_user = registration.objects.filter(Username=username).first()

        if existing_user:
            existing_user.Username = username
            existing_user.Password = password
            existing_user.B_id = branch_obj
            existing_user.User_level = user_level
            existing_user.Status = status
            existing_user.save()
            messages.success(request, "Updated successfully!")
        else:
            registration.objects.create(
                Username=username,
                Password=password,
                B_id=branch_obj,
                User_level=user_level,
                Status=status,
                Company=user.Company,
            )
            messages.success(request, "Successfully Registered!")

        return redirect(f'/user_reg/{user.id}?success=true')

    return render(request, 'user_reg.html', {
        'user': user,
        'user_data': user_data,
        'branch_list': branch_list,
        'default_branch_name': user.B_id.Branch_name,
    })

def search_user_names(request):
    query = request.GET.get('query', '').strip()
    branch_name = request.GET.get('branch_name', '')

    if not query:
        return JsonResponse([], safe=False)

    if branch_name == 'Head Office':
        users = registration.objects.filter(Username__icontains=query)
    else:
        users = registration.objects.filter(
            Username__icontains=query,
            B_id__Branch_name=branch_name
        )

    results = [{
        'Username': user.Username,
        'Password': user.Password,  
        'Branch_code': user.B_id.Branch_code,
        'Branch_name': user.B_id.Branch_name,
        'User_level': user.User_level,
        'Status': user.Status,
    } for user in users]

    return JsonResponse(results, safe=False)


def get_users_by_branch(request):
    user_id = request.GET.get('user_id', '')
    user = registration.objects.filter(id=user_id).first()
    if not user:
        return JsonResponse({'error': 'Invalid user'}, status=400)

    users = registration.objects.filter(B_id__Branch_name=user.B_id.Branch_name)

    data = [
        {
            'Username': u.Username,
            'Password': u.Password,
            'Branch_code': u.B_id.Branch_code,
            'Branch_name': u.B_id.Branch_name,
            'User_level': u.User_level,
        }
        for u in users
    ]

    return JsonResponse(data, safe=False)

def change_password(request, user_id):
    user = registration.objects.filter(id=user_id).first()
    if request.method == 'POST':
        username = request.POST.get('Username')
        current_password = request.POST.get('Password')
        new_password = request.POST.get('New_password')
        confirm_password = request.POST.get('Confirm_password')

        if not new_password:
            messages.error(request, 'New password cannot be empty.')

        elif new_password != confirm_password:
            messages.error(request, 'New password and confirmation password do not match.')

        else:
            reg = registration.objects.filter(Username=username, Password=current_password).first()
            if reg:
                reg.Password = new_password  
                reg.save() 
                messages.success(request, "Password updated successfully!")
            else:
                messages.error(request, 'Invalid current password.')

    return render(request, 'change_password.html', {'user': user})

class StaffForm(forms.ModelForm):
    class Meta:
        model = Staff
        exclude = ['Branch_code']
        fields = '__all__'
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
            'name': forms.TextInput(attrs={
                'autocomplete': 'off'
            }),
        }

def staff_registration(request, user_id):
    user = get_object_or_404(registration, id=user_id)
    branch_instance = branch.objects.filter(Branch_name=user.B_id.Branch_name).first()
    staff_id = request.POST.get('staff_id') or request.GET.get('staff_id')
    staff_instance = None

    if staff_id and staff_id.isdigit():
        staff_instance = Staff.objects.filter(id=int(staff_id)).first()

    if request.method == 'POST':
        form = StaffForm(request.POST, request.FILES, instance=staff_instance)

        if form.is_valid():
            staff = form.save(commit=False)
            staff.Branch_code = branch_instance.Branch_code

            photo_data = request.POST.get('photo_captured')
            if photo_data and photo_data.startswith('data:image'):
                format, imgstr = photo_data.split(';base64,')
                ext = format.split('/')[-1]
                staff.photo = ContentFile(base64.b64decode(imgstr), name=f"captured_photo.{ext}")
            elif 'photo' in request.FILES:
                staff.photo = request.FILES['photo']

            if 'signature' in request.FILES:
                staff.signature = request.FILES['signature']

            staff.save()

            msg = "Updated successfully!" if staff_instance else "Registered successfully!"
            messages.success(request, msg)
            return redirect('staff_registration', user_id=user.id)
        else:
            messages.error(request, "There were errors in the form.")
            print("Form errors:", form.errors)
    else:
        form = StaffForm(instance=staff_instance)

    return render(request, 'staff_registration.html', {
        'form': form,
        'user': user,
        'staff_id': staff_id or ''
    })

def get_staff_names(request, user_id):
    user = registration.objects.filter(id=user_id).first()
    if not user:
        return JsonResponse([], safe=False)

    try:
        branch_instance = branch.objects.get(Branch_name=user.B_id.Branch_name)
    except branch.DoesNotExist:
        return JsonResponse([], safe=False)

    query = request.GET.get('query', '')
    if query:
        matches = Staff.objects.filter(name__istartswith=query, Branch_code=branch_instance.Branch_code)
        data = []
        for staff in matches:
            data.append({
                'id': staff.id,  
                'name': staff.name,
                'dob': staff.dob.strftime('%Y-%m-%d') if staff.dob else '',
                'gender': staff.gender,
                'relation': staff.relation,
                'relation_name': staff.relation_name,
                'photo': staff.photo.url if staff.photo else '',
                'signature': staff.signature.url if staff.signature else '',
                'house_name': staff.house_name,
                'house_no': staff.house_no,
                'place': staff.place,
                'post_office': staff.post_office,
                'pincode': staff.pincode,
                'city': staff.city,
                'district': staff.district,
                'state': staff.state,
                'country': staff.country,
                'mobile1': staff.mobile1,
                'mobile2': staff.mobile2,
                'phone': staff.phone,
                'email': staff.email,
                'marital_status': staff.marital_status,
            })
        return JsonResponse(data, safe=False)
    else:
        return JsonResponse([], safe=False)

def account_schedule_form(request, user_id):
    user = registration.objects.filter(id=user_id).first()
    ac = acdet.objects.filter(Sub_code="0000")

    if not user:
        return HttpResponse("User not found", status=404)
        
    latest_account = acdet.objects.order_by('-Pkac_code').first()
    if latest_account and latest_account.Pkac_code.isdigit():
        next_account_code = str(int(latest_account.Pkac_code) + 1)
    else:
        next_account_code = "1003"

    if request.method == 'POST':
        account_code = request.POST.get('accountCode')
        account_name = request.POST.get('accountName')
        account_nature = request.POST.get('accountNature')
        account_type = request.POST.get('accountType')
        sub_ledger = request.POST.get('subLedger')
        ho_branch = request.POST.get('hoBranch')  
        schedule_code = request.POST.get('scheduleCode')

        existing_user = acdet.objects.filter(Pkac_code=account_code)
        print("existing_user:",existing_user)
        if existing_user:
            for x_user in existing_user:
                x_user.Company = user.Company
                
                if schedule_code:
                    schedule_parts = schedule_code.split(' ')
                    if len(schedule_parts) >= 3:
                        x_user.Sh_code = schedule_parts[0]
                        x_user.Sh_name = schedule_parts[2]
                    else:
                        x_user.Sh_code = ''
                        x_user.Sh_name = ''
                
                x_user.Pkac_code = account_code
                x_user.Ac_name = account_name
                x_user.save()
            messages.success(request, "Updated successfully!")
        else:
            if schedule_code:
                schedule_parts = schedule_code.split(' ')
                if len(schedule_parts) >= 3:
                    schedule_sh_code = schedule_parts[0]
                    schedule_sh_name = schedule_parts[2]
                else:
                    schedule_sh_code = ''
                    schedule_sh_name = ''
            else:
                schedule_sh_code = ''
                schedule_sh_name = ''
            
            acdet.objects.create(
                Company=user.Company,
                Sh_code=schedule_sh_code,
                Pkac_code=account_code,
                Ac_name=account_name,
                Ac_type=account_type,
                Ac_nature=account_nature,
                HOBR=ho_branch,
                Sys_date_time=timezone.now(),
                Sub_l=sub_ledger,
                Sh_name=schedule_sh_name,  
            )
            messages.success(request, "Successfully Registered!")
            return redirect(f'/account_schedule_form/{user.id}')

    return render(request, 'account_schedule_form.html', {
        'user': user,
        'next_account_code': next_account_code
    })


def search_account_names(request):
    query = request.GET.get('query', '').strip()
    if query:
        raw_accounts = acdet.objects.filter(Ac_name__icontains=query).values(
            'Pkac_code', 'Ac_name', 'Ac_nature', 'Sh_code', 'Sh_name', 'Ac_type', 'HOBR', 'Sub_l'
        )
        seen_keys = set()
        unique_accounts = []
        for acc in raw_accounts:
            key = (acc['Pkac_code'], acc['Ac_name'])
            if key not in seen_keys:
                seen_keys.add(key)
                unique_accounts.append(acc)

        return JsonResponse(unique_accounts, safe=False)
    
    return JsonResponse([], safe=False)

def search_account_code(request):
    query = request.GET.get('query', '').strip() 
    if query:
        raw_accounts = acdet.objects.filter(Pkac_code__icontains=query).values(
    'Pkac_code', 'Ac_name')  
        seen_keys = set()
        unique_accounts = []
        for acc in raw_accounts:
            key = (acc['Pkac_code'], acc['Ac_name'])
            if key not in seen_keys:
                seen_keys.add(key)
                unique_accounts.append(acc)
        return JsonResponse(unique_accounts, safe=False)
    return JsonResponse([], safe=False) 


def sub_ledger(request, user_id):
    user = registration.objects.filter(id=user_id).first()
    ac = acdet.objects.filter(Sub_code = "0000")
    
    if not user:
        return HttpResponse("User not found", status=404)
    
    if request.method == "POST":
        account_code = request.POST.get('account_code')
        account_name = request.POST.get('account_name')
        account_nature = request.POST.get('accountNature') 
        account_type = request.POST.get('accountType')
        schedule_code = request.POST.get('scheduleCode')
        branch = request.POST.get('branch')
        sub_account_code = request.POST.get('Sub_code')
        sub_account_name = request.POST.get('Sub_name')
        if schedule_code:
            scheduleCode = schedule_code.split(' ')[0]
        else:
            scheduleCode = '' 
        error = 0
        for i in ac:
            if account_name.strip().lower() == i.Ac_name.strip().lower() and account_code.strip().lower() == i.Pkac_code.strip().lower():
                if account_nature == i.Ac_nature and account_type == i.Ac_type and scheduleCode == i.Sh_code:
                    break
                else:
                    error += 1
            else:
                error += 1
        if error == len(ac):
            messages.success(request, "Main Head Account details are incorrect!!") 
            return render(request, 'sub_ledger.html', {
                'user': user,
                })

        latest_account = acdet.objects.filter(Pkac_code=account_code).order_by('-Sub_code').first()
        if latest_account and latest_account.Sub_code.isdigit():
            next_account_code = str(int(latest_account.Sub_code) + 1).zfill(4)

        acdet_instance = acdet.objects.filter(Pkac_code=account_code).first()
    
        if acdet.objects.filter(Pkac_code=account_code,Sub_name=sub_account_name).exists():
            messages.success(request, "This subLedger already exists!!")
            return render(request, 'sub_ledger.html', {'user': user, 'next_account_code': next_account_code})

       
        acdet(
            Pkac_code=account_code,
            Ac_name=account_name,
            Ac_type=acdet_instance.Ac_type,
            Ac_nature=acdet_instance.Ac_nature,
            Sh_code=acdet_instance.Sh_code,
            Sh_name=acdet_instance.Sh_name,
            Company=acdet_instance.Company,
            Sub_l="yes", 
            HOBR=acdet_instance.HOBR,
            Sys_date_time=timezone.now(),
            Sub_code=str(next_account_code) if next_account_code else "0001",
            Sub_name=sub_account_name,
            Branch=branch
        ).save()

        return redirect(f'/sub_ledger/{user.id}?success=true')

    return render(request, 'sub_ledger.html', {
        'user': user,
    })


def search_s_account_name(request):
    query = request.GET.get('query', '').strip()
    if query:
        raw_accounts = acdet.objects.filter(Sub_l="yes", Ac_name__icontains=query).values(
            'Pkac_code', 'Ac_name', 'Ac_nature', 'Sh_code', 'Sh_name', 'Ac_type', 'HOBR', 'Sub_l','Sub_code'
        ).order_by('-Sub_code')
        seen = set()
        unique_accounts = []
        for acc in raw_accounts:
            key = (acc['Pkac_code'], acc['Ac_name'])
            if key not in seen:
                seen.add(key)
                unique_accounts.append(acc)
        return JsonResponse(unique_accounts, safe=False)
    return JsonResponse([], safe=False)

def search_s_account_code(request):
    query = request.GET.get('query', '').strip()
    if query:
        raw_accounts = acdet.objects.filter(Sub_l="yes", Pkac_code__icontains=query).values(
            'Pkac_code', 'Ac_name', 'Ac_nature', 'Sh_name', 'Sh_code', 'Ac_type','Sub_code'
        ).order_by('-Sub_code')
        seen = set()
        unique_accounts = []
        for acc in raw_accounts:
            key = (acc['Pkac_code'], acc['Ac_name'])
            if key not in seen:
                seen.add(key)
                unique_accounts.append(acc)
        return JsonResponse(unique_accounts, safe=False)
    return JsonResponse([], safe=False)

from django.db.models import Q

def search_sub_account(request):
    query = request.GET.get('query', '').strip()
    query1 = request.GET.get('query1', '').strip()
    if query:
        accounts = acdet.objects.filter(
            Pkac_code=query1
        ).filter(
            Q(Sub_name__icontains=query) | Q(Sub_code__icontains=query)
        ).exclude(Sub_code="0000") 
        result = list(accounts.values('Sub_code', 'Sub_name', 'Branch')) 
        return JsonResponse(result, safe=False)
    return JsonResponse([], safe=False)  

def get_next_subcode(request):
    account_code = request.GET.get('account_code')
    next_code = "0001"
    if account_code:
        latest_account = acdet.objects.filter(Pkac_code=account_code).order_by('-Sub_code').first()
        if latest_account and latest_account.Sub_code.isdigit():
            next_account_code = str(int(latest_account.Sub_code) + 1).zfill(4)

    return JsonResponse({'next_sub_code': next_code})


from django.db.models import Q

def search_sub_account(request):
    query = request.GET.get('query', '').strip()
    if not query:
        return JsonResponse([], safe=False)

    try:
        subledgers = acdet.objects.filter(Pkac_code=query).exclude(Sub_code="0000")
        data = [{"Sub_code": s.Sub_code, "Sub_name": s.Sub_name} for s in subledgers]
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def search_sub_account_j(request):
    query = request.GET.get('query', '').strip()
    query1 = request.GET.get('query1', '').strip()
    if not query:
        return JsonResponse([], safe=False)

    try:
        subledgers = acdet.objects.filter(Pkac_code=query,Sub_code=query1).exclude(Sub_code="0000")
        data = [{"Sub_code": s.Sub_code, "Sub_name": s.Sub_name} for s in subledgers]
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def search_sub_account_code(request):
    query = request.GET.get('query', '').strip()
    query1 = request.GET.get('query1', '').strip()

    if query:
        accounts = acdet.objects.filter(
            Pkac_code=query1,
            Sub_code__icontains=query,
        ).values('Sub_code', 'Sub_name', 'Branch')
        return JsonResponse(list(accounts), safe=False)
    return JsonResponse([], safe=False)

import datetime

def cash_book_entry_view(request, user_id):
    user = registration.objects.filter(id=user_id).first()
    account_codes = acdet.objects.all()

    date_str = request.POST.get('date') if request.method == 'POST' else request.GET.get('date')
    if date_str:
        try:
            date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            date = datetime.date.today()
    else:
        date = datetime.date.today()

    subquery = temp_daybook.objects.filter(
        Ac_date=OuterRef('Ac_date'),
        Fk_accode=OuterRef('Fk_accode'),
        Trans_amount=OuterRef('Trans_amount'),
        Narration=OuterRef('Narration'),
        Sub_code=OuterRef('Sub_code'),
        Type="c",
        User_id=user.id
    ).values('Ac_date', 'Fk_accode', 'Trans_amount', 'Narration', 'Sub_code')\
    .annotate(min_id=Min('id')).values('min_id')

    entries = temp_daybook.objects.filter(
        id__in=Subquery(subquery)
    ).filter(User_id=user.id, Type="c", Ac_date=date).exclude(Fk_accode="1001").order_by('id')

    latest_transaction = temp_daybook.objects.order_by('-Trans_id').first()
    if latest_transaction:
        next_trans_code = str(latest_transaction.Trans_id + 1)
    else:
        next_trans_code = "1"

    def extract_subledger_parts(sub_ledger):
        parts = sub_ledger.split('-')
        if len(parts) >= 2:
            return parts[0], parts[1]
        return '', ''

    if request.method == 'POST':
        entry_id = request.POST.get('entry_id')
        mode = request.POST.get('mode')
        account_code = request.POST.get('account_code')
        account_name = request.POST.get('account_name')
        amount = request.POST.get('amount')
        narration = request.POST.get('narration')
        sub_ledger = request.POST.get('sub_ledger')

        if mode == "credit":
            mode_rev = "debit"
        else:
            mode_rev = "credit"

        

        if not any(ac.Pkac_code == account_code and ac.Ac_name == account_name for ac in account_codes):
            messages.success(request, "Invalid Account!!")
            return redirect('cash_book_entry', user_id=user.id)

        if not account_name:
            account = acdet.objects.filter(Pkac_code=account_code).first()
            account_name = account.Ac_name if account else ''

        if sub_ledger == []:
            sub_code, sub_name = extract_subledger_parts(sub_ledger)

            if not any(sl.Sub_code.strip().lower() == sub_code.strip().lower() and sl.Sub_name.strip().lower() == sub_name.strip().lower() for sl in account_codes):
                messages.success(request, "Invalid SubLedger!!")
                return redirect('cash_book_entry', user_id=user.id)
        else:
            sub_code = ""
            sub_name = ""

        if entry_id:
            original_entry = get_object_or_404(temp_daybook, id=entry_id)
            pair_entries = temp_daybook.objects.filter(Trans_id=original_entry.Trans_id)

            for entry in pair_entries:
                entry.Ac_date = date
                entry.Mode = mode if entry.Mode.lower() == mode.lower() else mode_rev
                entry.Fk_accode = account_code
                entry.Trans_amount = amount
                entry.Narration = narration
                entry.Sub_code = sub_code
                entry.User_id = user.id
                entry.Branch_code = user.B_id
                entry.Type = "c"
                entry.save()


            messages.success(request, "Entry updated successfully.")
        else:
            temp_daybook.objects.create(
                Ac_date=date,
                Mode=mode,
                Fk_accode=account_code if mode == "debit" else "1001",
                Sub_code=sub_code,
                Branch_code=user.B_id,
                User_id=user.id,
                Trans_id=next_trans_code,
                Trans_amount=amount,
                crcode="1001" if mode == "debit" else  account_code,
                Narration=narration,
                Type="c",
            )
            temp_daybook.objects.create(
                Ac_date=date,
                Mode=mode_rev,
                Fk_accode=account_code if mode == "credit" else "1001",
                Sub_code=sub_code,
                Branch_code=user.B_id,
                User_id=user.id,
                Trans_id=next_trans_code,
                Trans_amount=amount,
                crcode="1001" if mode == "credit" else  account_code,
                Narration=narration,
                Type="c",
            )
            messages.success(request, "Entry added successfully.")

        return redirect('cash_book_entry', user_id=user.id)

    return render(request, 'cash_book_entry.html', {
        'entries': entries,
        'user': user,
        'account_codes': account_codes,
        'selected_date': date  
    })


def delete_cash_entry(request, entry_id, user_id):
    if request.method == 'POST':
        print("ENTRY id:",entry_id)
        entry = get_object_or_404(temp_daybook, pk=entry_id)
        print("ENTRY id:",entry_id)
        trans_id = entry.Trans_id

        temp_daybook.objects.filter(Trans_id=trans_id).delete()
        messages.success(request, f"Transaction {trans_id} deleted successfully.")
    
        return redirect('cash_book_entry', user_id=user_id)
    else :
        print("KOii")


def search_account_names_daybook(request):
    query = request.GET.get('query', '').strip()
    if query:
        raw_accounts = acdet.objects.filter(Ac_name__icontains=query).exclude(Pkac_code__in=["1001", "1002"]).values(
            'Pkac_code', 'Ac_name')
        seen_keys = set()
        unique_accounts = []
        for acc in raw_accounts:
            key = (acc['Pkac_code'], acc['Ac_name'])
            if key not in seen_keys:
                seen_keys.add(key)
                unique_accounts.append(acc)

        return JsonResponse(unique_accounts, safe=False)
   
    return JsonResponse([], safe=False)

def search_account_code_daybook(request):
    query = request.GET.get('query', '').strip()
    if query:
        raw_accounts = acdet.objects.filter(Pkac_code__icontains=query).exclude(Pkac_code__in=["1001", "1002"]).values(
    'Pkac_code', 'Ac_name')  
        seen_keys = set()
        unique_accounts = []
        for acc in raw_accounts:
            key = (acc['Pkac_code'], acc['Ac_name'])
            if key not in seen_keys:
                seen_keys.add(key)
                unique_accounts.append(acc)
        return JsonResponse(unique_accounts, safe=False)
    return JsonResponse([], safe=False) 

def bankbook(request, user_id):
    user = registration.objects.filter(id=user_id).first()
    account_codes = acdet.objects.all()
    bank_select = acdet.objects.filter(Pkac_code="1002").exclude(Sub_code="0000")
    date_str = request.POST.get('date') if request.method == 'POST' else request.GET.get('date')
    if date_str:
        try:
            date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            date = datetime.date.today()
    else:
        date = datetime.date.today()

    subquery = temp_daybook.objects.filter(
        Ac_date=OuterRef('Ac_date'),
        Fk_accode=OuterRef('Fk_accode'),
        Trans_amount=OuterRef('Trans_amount'),
        Narration=OuterRef('Narration'),
        Sub_code=OuterRef('Sub_code'),
        Type="b",
        User_id=user.id
    ).values('Ac_date', 'Fk_accode', 'Trans_amount', 'Narration', 'Sub_code')\
    .annotate(min_id=Min('id')).values('min_id')

    entries = temp_daybook.objects.filter(
        id__in=Subquery(subquery)
    ).filter(User_id=user.id, Type="b", Ac_date=date).exclude(Fk_accode="1002").order_by('id')

    latest_transaction = temp_daybook.objects.order_by('-Trans_id').first()
    if latest_transaction:
        next_trans_code = str(latest_transaction.Trans_id + 1)
    else:
        next_trans_code = "1"

    def extract_subledger_parts(sub_ledger):
        parts = sub_ledger.split('-')
        if len(parts) >= 2:
            return parts[0], parts[1]
        return '', ''

    if request.method == 'POST':
        entry_id = request.POST.get('entry_id')
        mode = request.POST.get('mode')
        account_code = request.POST.get('account_code')
        account_name = request.POST.get('account_name')
        amount = request.POST.get('amount')
        narration = request.POST.get('narration')
        sub_ledger = request.POST.get('sub_ledger')
        bank = request.POST.get('select_bank')

        if mode == "credit":
            mode_rev = "debit"
        else:
            mode_rev = "credit"

        if not any(ac.Pkac_code == account_code and ac.Ac_name == account_name for ac in account_codes):
            messages.success(request, "Invalid Account!!")
            return redirect('bankbook', user_id=user.id)

        if not account_name:
            account = acdet.objects.filter(Pkac_code=account_code).first()
            account_name = account.Ac_name if account else ''

        if sub_ledger == []:
            sub_code, sub_name = extract_subledger_parts(sub_ledger)

            if not any(sl.Sub_code.strip().lower() == sub_code.strip().lower() and sl.Sub_name.strip().lower() == sub_name.strip().lower() for sl in account_codes):
                messages.success(request, "Invalid SubLedger!!")
                return redirect('cash_book_entry', user_id=user.id)
        else:
            sub_code = ""
            sub_name = ""

        if entry_id:
            original_entry = get_object_or_404(temp_daybook, id=entry_id)
            pair_entries = temp_daybook.objects.filter(Trans_id=original_entry.Trans_id)

            for entry in pair_entries:
                entry.Ac_date = date
                entry.Mode = mode if entry.Mode.lower() == mode.lower() else mode_rev
                entry.Fk_accode = account_code
                entry.Trans_amount = amount
                entry.Narration = narration
                entry.Sub_code = sub_code
                entry.User_id = user.id
                entry.Branch_code = user.B_id
                entry.Bank = bank
                entry.Type = "b"
                entry.save()

            messages.success(request, "Entry updated successfully.")
        else:
            temp_daybook.objects.create(
                Ac_date=date,
                Mode=mode,
                Fk_accode=account_code if mode == "debit" else "1002",
                Sub_code=sub_code,
                Branch_code=user.B_id,
                User_id=user.id,
                Trans_id=next_trans_code,
                Trans_amount=amount,
                crcode = "1002" if mode == "credit" else account_code,
                Narration=narration,
                Bank=bank,
                Type="b",
            )
            temp_daybook.objects.create(
                Ac_date=date,
                Mode=mode_rev,
                Fk_accode=account_code if mode == "credit" else "1002",
                Sub_code=sub_code,
                Branch_code=user.B_id,
                User_id=user.id,
                Trans_id=next_trans_code,
                Trans_amount=amount,
                crcode = "1002" if mode == "debit" else account_code,
                Narration=narration,
                Bank=bank,
                Type="b",
            )
            messages.success(request, "Entry added successfully.")

        return redirect('bankbook', user_id=user.id)

    return render(request, 'bankbook.html', {
        'entries': entries,
        'user': user,
        'account_codes': account_codes,
        'selected_date': date,
        'bank_select': bank_select    
    })

def delete_bank_entry(request, entry_id, user_id):
    entry = get_object_or_404(temp_daybook, pk=entry_id)
    temp_daybook.objects.filter(Trans_id=entry.Trans_id).delete()
    return redirect('bankbook', user_id=user_id)

def journal(request, user_id):
    user = get_object_or_404(registration, id=user_id)
    account_list = acdet.objects.all()
    
    return render(request, 'journal.html', {
        'user': user,
        'account_list': account_list,
    })

@csrf_exempt
def save_journal_entries(request, user_id):
    user = get_object_or_404(registration, id=user_id)
    
    latest_transaction = temp_daybook.objects.order_by('-Trans_id').first()
    next_trans_code = latest_transaction.Trans_id + 1 if latest_transaction else 1

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            narration = data.get('narration')
            entries = data.get('entries', [])

            if not narration or not entries:
                return JsonResponse({'status': 'error', 'message': 'Invalid data'})

            saved_entries = []

            for entry in entries:
                new_entry = temp_daybook.objects.create(
                    Ac_date=now().date(),
                    Mode=entry['mode'], 
                    Fk_accode=entry.get('account_code', ''),
                    Sub_code=entry.get('sub_code', ''),
                    Trans_amount=entry['amount'],
                    Narration=entry.get('remark', ''),
                    Remark=narration,
                    Type="j",
                    Branch_code=str(user.B_id),
                    User_id=user.id,
                    Trans_id=next_trans_code,
                )
                saved_entries.append(new_entry)

            for entry in saved_entries:
                for other in saved_entries:
                    if (
                        other != entry and
                        other.Trans_amount == entry.Trans_amount and
                        other.Mode != entry.Mode and
                        not other.crcode and not entry.crcode
                    ):
                        entry.crcode = other.Fk_accode
                        other.crcode = entry.Fk_accode
                        entry.save()
                        other.save()
                        break

            return JsonResponse({'status': 'success'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid method'})

def loop(request, user_id):
    user = registration.objects.filter(id=user_id).first()
    branch_obj = branch.objects.filter(Branch_name=user.B_id.Branch_name).first()
    branch_obj = branch.objects.get(Branch_code='Tcr')
    for i in range(1,1000):
        registration.objects.create(
                Username=i,
                Password=i,
                B_id=branch_obj,
                User_level="Entry",
                Status="Opened",
                Company=user.Company,
            )
    return render(request, 'index.html', {'user': user})
