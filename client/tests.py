from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User


class ClientAuthTests(TestCase):
	def test_register_get_shows_form(self):
		url = reverse('client-register')
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, '<form')

	def test_register_post_creates_user_and_redirects(self):
		url = reverse('client-register')
		data = {
			'username': 'newuser',
			'password1': 'Testpass123',
			'password2': 'Testpass123',
		}
		response = self.client.post(url, data)
		# should redirect to login
		self.assertEqual(response.status_code, 302)
		self.assertTrue(User.objects.filter(username='newuser').exists())

	def test_login_with_valid_credentials(self):
		username = 'tester'
		password = 'Testpass123'
		User.objects.create_user(username=username, password=password)

		url = reverse('client-login')
		response = self.client.post(url, {'username': username, 'password': password})
		# successful login redirects to LOGIN_REDIRECT_URL ('/')
		self.assertEqual(response.status_code, 302)
		self.assertEqual(response['Location'], '/')

	def test_login_with_invalid_credentials_shows_error(self):
		url = reverse('client-login')
		response = self.client.post(url, {'username': 'noone', 'password': 'badpass'})
		# invalid login should re-render form with status 200 and show error message
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Por favor, introduce un nombre de usuario y contraseña correctos')

	def test_logout_redirects_and_clears_session(self):
		username = 'tester2'
		password = 'Testpass123'
		User.objects.create_user(username=username, password=password)
		# log in via the test client
		self.client.login(username=username, password=password)
		# ensure session has auth id
		self.assertIn('_auth_user_id', self.client.session)

		url = reverse('client-logout')
		response = self.client.get(url)
		# LogoutView redirects to login page name
		self.assertEqual(response.status_code, 302)
		# session should no longer have auth id
		self.assertNotIn('_auth_user_id', self.client.session)
