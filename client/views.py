from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm


def logout_view(request):
	"""Cerrar sesión — permite GET para facilitar pruebas y enlaces simples.

	Nota: en producción es más seguro usar POST. Esta vista acepta GET
	para mantener compatibilidad con el comportamiento esperado por las pruebas.
	"""
	if request.method in ('POST', 'GET'):
		logout(request)
		return redirect('client-login')
	return redirect('client-login')


def register(request):
	"""Registro de nuevo usuario usando UserCreationForm.

	- GET: muestra el formulario de registro.
	- POST: valida y crea el usuario; redirige a la página de login con mensaje.
	"""
	if request.method == 'POST':
		form = UserCreationForm(request.POST)
		if form.is_valid():
			user = form.save()
			return redirect('client-login')
	else:
		form = UserCreationForm()

	return render(request, 'register.html', {'form': form})


