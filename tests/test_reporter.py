"""
@author: Gareth Brown
@contact: gareth@mesoform.com
@date: 2017
"""
from unittest import TestCase, TextTestRunner, TestSuite, skip
from builder import GcpAuth
from reporter.stackdriver import Metrics, AlertPolicy
from google.cloud.monitoring_v3 import MetricServiceClient, \
    AlertPolicyServiceClient, NotificationChannelServiceClient
from google.cloud.monitoring_v3.types import AlertPolicy as GoogleAlertPolicy
from google.cloud.monitoring_v3.types import NotificationChannel
from google.api_core.exceptions import InvalidArgument
from google.protobuf import message_factory

_TEST_CREDENTIALS_FILE_PATH = 'resources/gcp_token.json'
_TEST_ALERT_POLICY_ID = \
    'projects/gb-me-services/alertPolicies/7522594986680907020'


class TestReporterMetrics(TestCase):
    @classmethod
    def setUpClass(cls):
        with open(_TEST_CREDENTIALS_FILE_PATH) as f:
            cls.gcp_auth = GcpAuth(f)
        cls.client = Metrics("gb-me-services",
                             cls.gcp_auth.credentials,
                             [
                                 {
                                     "project_id": "my-project",
                                     "cost": 22.22,
                                     "time_window": "2hr"
                                 }
                             ])

    def test_client_setup(self):
        self.assertIsInstance(self.client, MetricServiceClient)

    def test_send_metrics(self):
        self.assertEqual(self.client.send_metrics(), None)


class TestReporterAlertPolicy(TestCase):
    @classmethod
    def setUpClass(cls):
        with open(_TEST_CREDENTIALS_FILE_PATH) as f:
            cls.gcp_auth = GcpAuth(f)
        cls.client = AlertPolicy(
            "gb-me-services",
            cls.gcp_auth.credentials,
            {}
        )
        cls.notification_channel = NotificationChannel()
        cls.policy = GoogleAlertPolicy()

        cls.notification_channel.type = 'email'
        cls.notification_channel.display_name = 'support@mesoform.com'
        cls.notification_channel.description = 'Main Mesoform support team'
        cls.notification_channel.labels[
            'email_address'] = 'support@mesoform.com'
        new_channel = NotificationChannelServiceClient(
            credentials=cls.gcp_auth.credentials)
        created_channel = new_channel.create_notification_channel(
            cls.client.monitoring_project_path, cls.notification_channel)

        cls.policy.display_name = "magic alert policy"
        assert not cls.policy.HasField('documentation')
        cls.policy.documentation.content = 'link to my documentation'
        cls.policy.documentation.mime_type = 'text/markdown'
        cls.policy.combiner = cls.policy.AND

        # print(created_channel.ListFields())
        cls.policy.notification_channels.append(created_channel.name)
        condition1 = cls.policy.conditions.add()
        condition1.display_name = 'my magic alert policy condition 1'
        condition1.condition_threshold.threshold_value = 22.00
        condition1.condition_threshold.filter = 'resource.type=global AND metric.label.time_window = "2hr" AND metric.type = "custom.googleapis.com/billing/my-project"'
        condition1.condition_threshold.duration.seconds = 60
        condition1.condition_threshold.comparison = 1
        condition1.condition_threshold.trigger.count = 3

    def test_client_setup(self):
        self.assertIsInstance(self.client, AlertPolicyServiceClient)

    def test_list_policies_contains_id(self):
        policy_ids = list()
        policies = self.client.list_alert_policies(
            self.client.project_path(self.client.monitoring_project))
        for policy in policies:
            policy_ids.append(policy.name)

        self.assertIn(_TEST_ALERT_POLICY_ID, policy_ids)

    def test_get_policy(self):
        print(self.client.get_alert_policy(_TEST_ALERT_POLICY_ID))
        self.assertIsInstance(
            self.client.get_alert_policy(_TEST_ALERT_POLICY_ID),
            GoogleAlertPolicy)

    @skip
    def test_create_policy_fails(self):
        self.assertRaises(
            self.client.create_alert_policy(self.client.monitoring_project_path,
                                            {}), InvalidArgument)

    def test_create_policy_succeeds(self):
        self.assertIsInstance(
            self.client.create_alert_policy(
                self.client.monitoring_project_path,
                self.policy),
            GoogleAlertPolicy)


def suite():
    test_suite = TestSuite()
    test_suite.addTest(
        TestReporterMetrics('test_get_credentials_without_file_returns'))
    test_suite.addTest(
        TestReporterMetrics('test_send_metrics'))
    test_suite.addTest(
        TestReporterAlertPolicy('test_list_policies_contains_id'))
    return test_suite


if __name__ == '__main__':
    runner = TextTestRunner(verbosity=2)
    # noinspection PyCallByClass
    runner.run(suite())
