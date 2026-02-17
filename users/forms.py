from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Sector
from django.contrib.auth.models import Group
import datetime

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
        self.fields['managed_sectors'].queryset = Sector.objects.all()
        self.fields['managed_sectors'].required = False
        self.fields['managed_sectors'].help_text = "Select sectors this water tender will manage"
        self.fields['managed_sectors'].label = "Managed Sectors"
    
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
        
        # Auto-set membership_form_date if membership_form_submitted is checked
        if cleaned_data.get('membership_form_submitted') and not cleaned_data.get('membership_form_date'):
            cleaned_data['membership_form_date'] = datetime.date.today()
        
        # Auto-set membership_approved_date if is_verified is checked
        if cleaned_data.get('is_verified') and not cleaned_data.get('membership_approved_date'):
            cleaned_data['membership_approved_date'] = datetime.date.today()
            
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

class ProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'address']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        } 


class TermsSignupForm(forms.Form):
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
        # No persistence needed beyond validation, but method must exist
        return user