from django.contrib.auth.models import User
from django.test import TestCase

from apps.facilities.models import Facility

from ..models import OperationAdjustment


class SaveFromJsonTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner', password='password')
        self.other_user = User.objects.create_user(username='other', password='password')
        self.facility = Facility.objects.create(name='テスト施設', prefecture='東京都', address='渋谷区')

        self.base_data = {
            'app_type': 'new',
            'user': {'name': '使用者', 'kana': 'しようしゃ', 'tel': '090-0000-0000', 'email': 'u@ex.com'},
            'event': {'name': 'テスト催事', 'comment': ''},
            'facilities': [],
            'mic_counts': {'analog_rm': {'10mw': 1}},
        }

    def test_create_new_adjustment(self):
        """save_from_json() で新規 OperationAdjustment が DB に保存されること"""
        adj = OperationAdjustment.save_from_json(self.base_data, user=self.user)
        self.assertIsNotNone(adj.pk)
        self.assertEqual(adj.event_name, 'テスト催事')
        self.assertEqual(adj.user_name, '使用者')
        self.assertEqual(adj.status, 'draft')
        self.assertEqual(adj.user, self.user)

    def test_update_existing_draft(self):
        """同一ユーザーが自分の下書きを更新できること"""
        adj = OperationAdjustment.save_from_json(self.base_data, user=self.user)

        updated_data = {**self.base_data, 'id': adj.pk, 'event': {'name': '更新後催事'}}
        updated_adj = OperationAdjustment.save_from_json(updated_data, user=self.user)

        self.assertEqual(updated_adj.pk, adj.pk)
        self.assertEqual(updated_adj.event_name, '更新後催事')

    def test_cannot_update_submitted_adjustment(self):
        """送信済み（submitted）の調整届は変更できないこと"""
        adj = OperationAdjustment.save_from_json(self.base_data, user=self.user, status='submitted')

        update_data = {**self.base_data, 'id': adj.pk, 'event': {'name': '変更しようとする催事'}}
        with self.assertRaises(ValueError):
            OperationAdjustment.save_from_json(update_data, user=self.user)

    def test_other_user_cannot_update_draft(self):
        """他ユーザーの下書きは編集できないこと（PermissionError）"""
        adj = OperationAdjustment.save_from_json(self.base_data, user=self.user)

        update_data = {**self.base_data, 'id': adj.pk, 'event': {'name': '不正な更新'}}
        with self.assertRaises(PermissionError):
            OperationAdjustment.save_from_json(update_data, user=self.other_user)

    def test_invalid_facility_id_raises_error(self):
        """存在しない施設 ID を含む場合は ValueError が発生すること"""
        data_with_bad_facility = {
            **self.base_data,
            'facilities': [{'id': 99999, 'name': '幽霊施設', 'start_date': '2026-03-01', 'start_time': '10:00'}],
        }
        with self.assertRaises(ValueError):
            OperationAdjustment.save_from_json(data_with_bad_facility, user=self.user)

    def test_invalid_status_raises_error(self):
        """不正なステータスを指定した場合は ValueError が発生すること"""
        with self.assertRaises(ValueError):
            OperationAdjustment.save_from_json(self.base_data, user=self.user, status='invalid')

    def test_extra_53ch_flag(self):
        """extra_53ch フラグが '○' の場合は True、それ以外は False になること"""
        data_with_53ch = {**self.base_data, 'extra_53ch': '○'}
        adj = OperationAdjustment.save_from_json(data_with_53ch, user=self.user)
        self.assertTrue(adj.extra_53ch)

        data_without_53ch = {**self.base_data, 'extra_53ch': ''}
        adj2 = OperationAdjustment.save_from_json(data_without_53ch, user=self.user)
        self.assertFalse(adj2.extra_53ch)
