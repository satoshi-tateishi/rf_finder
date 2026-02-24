from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from .models import AuditLog
from .utils import log_action

class AuditLogTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.factory = RequestFactory()

    def test_log_action_with_user(self):
        log = log_action(user=self.user, action='TEST_ACTION', description='Test Description')
        self.assertEqual(AuditLog.objects.count(), 1)
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, 'TEST_ACTION')
        self.assertEqual(log.description, 'Test Description')

    def test_log_action_with_request(self):
        request = self.factory.get('/')
        request.user = self.user
        log = log_action(action='REQUEST_ACTION', description='Request Description', request=request)
        self.assertEqual(AuditLog.objects.count(), 1)
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, 'REQUEST_ACTION')
        # Check IP address (default for RequestFactory is 127.0.0.1)
        self.assertEqual(log.ip_address, '127.0.0.1')
