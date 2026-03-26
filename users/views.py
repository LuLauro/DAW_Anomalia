from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib.auth import login
from .forms import LoginForm, SignUpForm
from django.shortcuts import redirect
from users.utils import is_admin, is_tecnico, is_professor, is_coordenador
from users.utils import is_tecnico
from django.contrib.auth.decorators import user_passes_test, login_required

@login_required
@user_passes_test(is_tecnico)
def dashboard_tecnico(request):
    return render(request, 'tecnico/dashboard.html')
        
class CustomLoginView(LoginView):
        template_name = 'users/login.html'

        def get_success_url(self):
            user = self.request.user

            if is_admin(user):
                return '/dashboard/'
            elif is_tecnico(user):
                return '/tecnico/dashboard/'
            elif is_professor(user):
                return '/anomalias/'
            elif is_coordenador(user):
                return '/anomalias/'
            else:
                return '/'
    

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('users:login') # vai para login customizado

def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('anomalias:lista_anomalias')
    else:
        form = SignUpForm()
    return render(request, 'users/signup.html', {'form': form})
