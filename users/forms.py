from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Sector, MembershipApplication
from django.contrib.auth.models import Group
import datetime


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(item, initial) for item in data if item]
        if not data:
            return []
        return [single_file_clean(data, initial)]

class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(), required=False)
    confirm_password = forms.CharField(widget=forms.PasswordInput(), required=False)
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'role', 'phone_number', 'address',
                  'managed_sectors', 'is_verified', 'membership_form_submitted', 'membership_form_date',
                  'membership_approved_date', 'membership_rejected_reason', 'is_staff', 'is_superuser']
        widgets = {
            'is_staff': forms.HiddenInput(),
            'is_superuser': forms.HiddenInput(),
            'membership_form_date': forms.DateInput(attrs={'type': 'date'}),
            'membership_approved_date': forms.DateInput(attrs={'type': 'date'}),
            'membership_rejected_reason': forms.Textarea(attrs={'rows': 3}),
            'managed_sectors': forms.SelectMultiple(attrs={'class': 'form-control select2'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        visible_role_choices = [
            (value, label)
            for value, label in self.fields['role'].choices
            if value != CustomUser.WATER_TENDER
        ]
        if self.instance.pk and self.instance.role == CustomUser.WATER_TENDER:
            visible_role_choices.append((CustomUser.WATER_TENDER, 'Water Tender'))
        self.fields['role'].choices = visible_role_choices
        self.fields['managed_sectors'].queryset = Sector.objects.all()
        self.fields['managed_sectors'].required = False
        self.fields['managed_sectors'].help_text = "Select sectors this water tender will manage"
        self.fields['managed_sectors'].label = "Managed Sectors"
        self.fields['password'].help_text = "Leave blank to keep the current password."
        self.fields['confirm_password'].help_text = "Re-enter the password only when setting a new one."
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        # If this is an update (self.instance.pk exists) and username hasn't changed, skip validation
        if hasattr(self.instance, 'pk') and self.instance.pk and self.instance.username == username:
            return username
            
        # Check if username already exists
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError(f"Username '{username}' is already taken.")
        return username
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        role = cleaned_data.get('role')
        managed_sectors = cleaned_data.get('managed_sectors')
        
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords don't match")
        
        # Validate sectors are selected for water tenders
        if role == CustomUser.WATER_TENDER and not managed_sectors:
            self.add_error('managed_sectors', "Water tenders must be assigned to at least one sector.")
        elif role != CustomUser.WATER_TENDER:
            cleaned_data['managed_sectors'] = Sector.objects.none()

        # Auto-set membership_form_date if membership_form_submitted is checked
        if cleaned_data.get('membership_form_submitted') and not cleaned_data.get('membership_form_date'):
            cleaned_data['membership_form_date'] = datetime.date.today()

        # Auto-set membership_approved_date if is_verified is checked
        if cleaned_data.get('is_verified') and not cleaned_data.get('membership_approved_date'):
            cleaned_data['membership_approved_date'] = datetime.date.today()

        if cleaned_data.get('is_verified'):
            cleaned_data['membership_form_submitted'] = True
            if not cleaned_data.get('membership_form_date'):
                cleaned_data['membership_form_date'] = datetime.date.today()
            
        # Clear rejected reason if verified
        if cleaned_data.get('is_verified') and cleaned_data.get('membership_rejected_reason'):
            cleaned_data['membership_rejected_reason'] = ''
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get('password'):
            user.set_password(self.cleaned_data['password'])
        
        # Set is_staff and is_superuser based on role
        role = self.cleaned_data.get('role')
        if role == CustomUser.SUPERUSER:
            user.is_staff = True
            user.is_superuser = True
        elif role == CustomUser.WATER_TENDER:
            user.is_staff = True  # Water Tenders need staff access to admin panel
            user.is_superuser = False
        else:
            # Regular users aren't staff or superusers
            user.is_staff = False
            user.is_superuser = False
        
        if commit:
            user.save()
            
            # Handle many-to-many fields
            self.save_m2m()

            if role != CustomUser.WATER_TENDER:
                user.managed_sectors.clear()
            
            # Update user groups based on role
            user.groups.clear()
            try:
                if role == CustomUser.SUPERUSER:
                    admin_group = Group.objects.get(name='Administrators')
                    user.groups.add(admin_group)
                elif role == CustomUser.WATER_TENDER:
                    try:
                        water_tender_group = Group.objects.get(name='WaterTenders')
                        user.groups.add(water_tender_group)
                    except Group.DoesNotExist:
                        # Create the Water Tenders group if it doesn't exist
                        water_tender_group = Group.objects.create(name='WaterTenders')
                        user.groups.add(water_tender_group)
                else:
                    regular_group = Group.objects.get(name='RegularUsers')
                    user.groups.add(regular_group)
            except Group.DoesNotExist:
                # Groups don't exist yet, which is fine
                pass
                
        return user


class MembershipAdminEditForm(forms.ModelForm):
    class Meta:
        model = MembershipApplication
        fields = [
            'middle_name', 'gender', 'birth_date', 'place_of_birth',
            'civil_status', 'education', 'national_id_number', 'rcba_number', 'sector',
            'sitio', 'barangay', 'city', 'province',
            'is_tiller', 'lot_number', 'ownership_type',
            'land_owner', 'farm_manager', 'farm_location',
            'bufia_farm_location', 'farm_size',
            'land_proof_document', 'land_proof_notes',
            'payment_method', 'payment_status',
        ]
        widgets = {
            'middle_name': forms.TextInput(),
            'gender': forms.Select(),
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'place_of_birth': forms.TextInput(),
            'civil_status': forms.Select(),
            'education': forms.Select(),
            'national_id_number': forms.TextInput(),
            'rcba_number': forms.TextInput(),
            'sector': forms.Select(),
            'sitio': forms.TextInput(),
            'barangay': forms.TextInput(),
            'city': forms.TextInput(),
            'province': forms.TextInput(),
            'is_tiller': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'lot_number': forms.TextInput(),
            'ownership_type': forms.Select(),
            'land_owner': forms.TextInput(),
            'farm_manager': forms.TextInput(),
            'farm_location': forms.TextInput(),
            'bufia_farm_location': forms.TextInput(),
            'farm_size': forms.NumberInput(attrs={'step': '0.01'}),
            'land_proof_document': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf,image/*'}),
            'land_proof_notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'payment_method': forms.Select(),
            'payment_status': forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sector'].queryset = Sector.objects.filter(is_active=True).order_by('sector_number')
        self.fields['sector'].label = 'Declared/Application Sector'
        self.fields['sector'].help_text = 'The sector the member selected during the membership application.'
        self.fields['national_id_number'].label = 'National ID Number'
        self.fields['national_id_number'].help_text = 'Membership requirement supplied by the applicant.'
        self.fields['rcba_number'].label = 'RSBSA Number'
        self.fields['rcba_number'].help_text = 'Enter the BUFIA-issued RSBSA number when assigning the member to a sector.'
        self.fields['is_tiller'].label = 'Actual tiller'
        self.fields['bufia_farm_location'].help_text = 'Specific location of the farm within BUFIA coverage.'
        self.fields['land_proof_document'].help_text = 'Admin can review the uploaded land title, tenancy proof, or other readable document.'
        self.fields['land_proof_notes'].help_text = 'Applicant notes about the uploaded proof document.'
        self.fields['payment_method'].help_text = 'How the membership fee is expected or was received.'
        self.fields['payment_status'].help_text = 'Current payment state of the membership fee.'

        for field_name, field in self.fields.items():
            field.required = False
            if field_name != 'is_tiller':
                existing_class = field.widget.attrs.get('class', '').strip()
                if isinstance(field.widget, forms.Select):
                    field.widget.attrs['class'] = f'{existing_class} form-select'.strip()
                elif isinstance(field.widget, forms.NumberInput):
                    field.widget.attrs['class'] = f'{existing_class} form-control'.strip()
                elif isinstance(field.widget, forms.DateInput):
                    field.widget.attrs['class'] = f'{existing_class} form-control'.strip()
                elif isinstance(field.widget, forms.TextInput):
                    field.widget.attrs['class'] = f'{existing_class} form-control'.strip()

        if self.instance.pk and self.instance.land_proof_document and not self.instance.primary_land_proof.file_exists:
            self.fields['land_proof_document'].widget = forms.FileInput(
                attrs={'class': 'form-control', 'accept': '.pdf,image/*'}
            )
            self.fields['land_proof_document'].help_text = (
                'The previously saved proof file is missing from storage. Upload a replacement document to fix it.'
            )

        self.fields['payment_method'].initial = self.instance.payment_method or 'face_to_face'
        self.fields['payment_status'].initial = self.instance.payment_status or 'pending'


class MembershipProofUploadForm(forms.Form):
    land_proof_documents = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png,image/jpeg,image/png', 'multiple': True}),
    )
    land_proof_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    )

    def __init__(self, *args, require_document=False, existing_count=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_total_documents = 2
        self.existing_count = existing_count
        remaining_slots = max(self.max_total_documents - self.existing_count, 0)
        self.fields['land_proof_documents'].required = require_document
        self.fields['land_proof_documents'].label = 'Land Title / Tax Declaration Upload'
        if remaining_slots == 0:
            self.fields['land_proof_documents'].help_text = ''
        else:
            self.fields['land_proof_documents'].help_text = (
                f'Upload up to {remaining_slots} more PDF, JPG, JPEG, or PNG file{"s" if remaining_slots != 1 else ""}. '
                'Mobile phone photos are allowed if they are clear and readable. Maximum file size is 5 MB per file.'
            )
        self.fields['land_proof_notes'].label = 'Proof Notes'
        self.fields['land_proof_notes'].help_text = (
            'Optional note for BUFIA review.'
        )

    def clean_land_proof_documents(self):
        files = self.cleaned_data.get('land_proof_documents') or []
        total_files = self.existing_count + len(files)
        if total_files > self.max_total_documents:
            if self.existing_count == 0:
                raise forms.ValidationError('Upload up to 2 land title or tax declaration files only.')
            remaining_slots = max(self.max_total_documents - self.existing_count, 0)
            if remaining_slots == 0:
                raise forms.ValidationError('Maximum of 2 land title or tax declaration files already uploaded.')
            raise forms.ValidationError(
                f'You can upload {remaining_slots} more land title or tax declaration file{"s" if remaining_slots != 1 else ""} only.'
            )
        return files

class ProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'address']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        } 


class WalkInUserForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True
        self.fields['phone_number'].required = True

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'address']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
        }


class WalkInMembershipForm(forms.ModelForm):
    tax_declaration = forms.FileField(
        required=True,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png,image/jpeg,image/png'}),
        label='Tax Declaration',
    )
    title_of_land = forms.FileField(
        required=True,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png,image/jpeg,image/png'}),
        label='Title of Land',
    )
    requirements_complete = forms.BooleanField(
        required=False,
        initial=False,
        label='Requirements complete',
    )
    approve_if_ready = forms.BooleanField(
        required=False,
        initial=True,
        label='Approve immediately when payment and requirements are complete',
    )

    class Meta:
        model = MembershipApplication
        fields = [
            'middle_name', 'gender', 'birth_date', 'place_of_birth', 'civil_status', 'education',
            'national_id_number', 'rcba_number',
            'sitio', 'barangay', 'city', 'province',
            'is_tiller', 'lot_number', 'ownership_type', 'land_owner', 'farm_manager',
            'farm_location', 'farm_size',
            'valid_id_document', 'land_proof_notes',
            'sector', 'payment_method', 'payment_status',
        ]
        widgets = {
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'place_of_birth': forms.TextInput(attrs={'class': 'form-control'}),
            'civil_status': forms.Select(attrs={'class': 'form-select'}),
            'education': forms.Select(attrs={'class': 'form-select'}),
            'national_id_number': forms.TextInput(attrs={'class': 'form-control'}),
            'rcba_number': forms.TextInput(attrs={'class': 'form-control'}),
            'sitio': forms.TextInput(attrs={'class': 'form-control'}),
            'barangay': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'province': forms.TextInput(attrs={'class': 'form-control'}),
            'is_tiller': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'lot_number': forms.TextInput(attrs={'class': 'form-control'}),
            'ownership_type': forms.Select(attrs={'class': 'form-select'}),
            'land_owner': forms.TextInput(attrs={'class': 'form-control'}),
            'farm_manager': forms.TextInput(attrs={'class': 'form-control'}),
            'farm_location': forms.TextInput(attrs={'class': 'form-control'}),
            'farm_size': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valid_id_document': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf,image/*'}),
            'land_proof_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'sector': forms.Select(attrs={'class': 'form-select'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'payment_status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sector'].queryset = Sector.objects.filter(is_active=True).order_by('sector_number')
        self.fields['sector'].required = True
        self.fields['gender'].required = True
        self.fields['birth_date'].required = True
        self.fields['civil_status'].required = True
        self.fields['education'].required = True
        self.fields['national_id_number'].required = True
        self.fields['sitio'].required = True
        self.fields['barangay'].required = True
        self.fields['city'].required = True
        self.fields['province'].required = True
        self.fields['ownership_type'].required = True
        self.fields['farm_size'].required = True
        self.fields['valid_id_document'].required = True
        self.fields['rcba_number'].required = False
        self.fields['payment_method'].initial = 'face_to_face'
        self.fields['payment_status'].initial = 'pending'
        self.fields['national_id_number'].help_text = 'Record the applicant National ID Number before saving.'
        self.fields['rcba_number'].help_text = 'BUFIA admin should assign the member RSBSA number for the selected sector.'
        self.fields['is_tiller'].label = 'Actual tiller'
        self.fields['is_tiller'].help_text = (
            'Check this if the applicant is the person who actually cultivates or works the farm.'
        )
        self.fields['tax_declaration'].help_text = 'Upload a clear tax declaration file, just like the online membership requirement.'
        self.fields['title_of_land'].help_text = 'Upload a clear land title file, matching the regular membership requirements.'
        self.fields['valid_id_document'].help_text = 'Upload a clear National ID copy before saving the walk-in membership.'
        self.fields['land_proof_notes'].help_text = 'Optional explanation about the uploaded proof document.'
        self.fields['payment_method'].help_text = 'Walk-in memberships usually use over-the-counter payment.'
        self.fields['payment_status'].help_text = 'Use "Paid" only when payment has already been received and recorded.'

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('sector') and not (cleaned_data.get('rcba_number') or '').strip():
            self.add_error('rcba_number', 'RSBSA number is required when assigning a sector.')
        return cleaned_data


class TermsSignupForm(forms.Form):
    """Signup form with terms acceptance only."""
    accept_terms = forms.BooleanField(
        required=True,
        error_messages={
            'required': "You must agree to the BUFIA Terms & Conditions before continuing."
        },
        label="I have read and agree to the BUFIA Terms & Conditions"
    )

    def clean_accept_terms(self):
        value = self.cleaned_data.get('accept_terms')
        if not value:
            raise forms.ValidationError("You must accept the Terms & Conditions to continue.")
        return value

    def signup(self, request, user):
        return user


class MembershipApplicationForm(forms.ModelForm):
    """Form for membership application with admin-assigned sector flow."""
    class Meta:
        model = MembershipApplication
        fields = [
            'middle_name', 'gender', 'birth_date', 'place_of_birth',
            'civil_status', 'education', 'national_id_number',
            'sitio', 'barangay', 'city', 'province',
            'is_tiller', 'lot_number', 'ownership_type',
            'land_owner', 'farm_manager', 'farm_location',
            'bufia_farm_location', 'farm_size',
            'land_proof_document', 'land_proof_notes',
            'payment_method',
        ]
        widgets = {
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'place_of_birth': forms.TextInput(attrs={'class': 'form-control'}),
            'civil_status': forms.Select(attrs={'class': 'form-select'}),
            'education': forms.Select(attrs={'class': 'form-select'}),
            'national_id_number': forms.TextInput(attrs={'class': 'form-control'}),
            'sitio': forms.TextInput(attrs={'class': 'form-control'}),
            'barangay': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'province': forms.TextInput(attrs={'class': 'form-control'}),
            'is_tiller': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'lot_number': forms.TextInput(attrs={'class': 'form-control'}),
            'ownership_type': forms.Select(attrs={'class': 'form-select'}),
            'land_owner': forms.TextInput(attrs={'class': 'form-control'}),
            'farm_manager': forms.TextInput(attrs={'class': 'form-control'}),
            'farm_location': forms.TextInput(attrs={'class': 'form-control'}),
            'bufia_farm_location': forms.TextInput(attrs={'class': 'form-control'}),
            'farm_size': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'land_proof_document': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf,image/*', 'capture': 'environment'}),
            'land_proof_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['national_id_number'].required = True
        self.fields['national_id_number'].help_text = 'Enter the applicant National ID Number.'
