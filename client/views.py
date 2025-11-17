from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm


def register(request):
	"""Registro de nuevo usuario usando UserCreationForm.

	- GET: muestra el formulario de registro.
	- POST: valida y crea el usuario; redirige a la página de login con mensaje.
	"""
	if request.method == 'POST':
		form = UserCreationForm(request.POST)
		if form.is_valid():
			user = form.save()
			messages.success(request, 'Cuenta creada correctamente. Ya puedes iniciar sesión.')
			return redirect('client-login')
		else:
			messages.error(request, 'Por favor corrige los errores del formulario.')
	else:
		form = UserCreationForm()

	return render(request, 'register.html', {'form': form})


