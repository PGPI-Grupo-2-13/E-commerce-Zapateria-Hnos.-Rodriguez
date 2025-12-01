from django.test import TestCase
from django.db import IntegrityError
from seeder_flag.models import SeederStatus
from django.utils import timezone


class SeederFlagModelTests(TestCase):
	def test_default_values_and_str(self):
		s = SeederStatus.objects.create(name='initial_seed')
		# default executed is False
		self.assertFalse(s.executed)
		# executed_at set
		self.assertIsNotNone(s.executed_at)
		# __str__ contains Pending when not executed
		self.assertIn('Pending', str(s))

	def test_toggle_executed_changes_str(self):
		s = SeederStatus.objects.create(name='toggle_seed')
		s.executed = True
		s.save()
		s.refresh_from_db()
		self.assertTrue(s.executed)
		self.assertIn('Executed', str(s))

	def test_unique_name_constraint(self):
		SeederStatus.objects.create(name='unique_seed')
		with self.assertRaises(IntegrityError):
			# duplicate name should fail at DB level
			SeederStatus.objects.create(name='unique_seed')

	def test_executed_at_is_timestamp_on_create(self):
		before = timezone.now()
		s = SeederStatus.objects.create(name='ts_seed')
		self.assertTrue(s.executed_at >= before)
