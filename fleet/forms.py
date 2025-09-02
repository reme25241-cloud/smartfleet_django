from django import forms
from .models import UserAccount

class SignUpForm(forms.ModelForm):
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "placeholder": "Confirm Password",
            "class": "w-full bg-[#1C2541] text-white placeholder-gray-400 p-3 rounded-md outline-none focus:ring-2 focus:ring-blue-400"
        })
    )

    class Meta:
        model = UserAccount
        fields = ["fullname", "email", "phone", "password"]
        widgets = {
            "fullname": forms.TextInput(attrs={
                "placeholder": "Full Name",
                "class": "w-full bg-[#1C2541] text-white placeholder-gray-400 p-3 rounded-md outline-none focus:ring-2 focus:ring-blue-400"
            }),
            "email": forms.EmailInput(attrs={
                "placeholder": "Email",
                "class": "w-full bg-[#1C2541] text-white placeholder-gray-400 p-3 rounded-md outline-none focus:ring-2 focus:ring-blue-400"
            }),
            "phone": forms.TextInput(attrs={
                "placeholder": "Phone Number",
                "class": "w-full bg-[#1C2541] text-white placeholder-gray-400 p-3 rounded-md outline-none focus:ring-2 focus:ring-blue-400"
            }),
            "password": forms.PasswordInput(attrs={
                "placeholder": "Password",
                "class": "w-full bg-[#1C2541] text-white placeholder-gray-400 p-3 rounded-md outline-none focus:ring-2 focus:ring-blue-400"
            }),
        }
