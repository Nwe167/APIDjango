from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from .models import File, Permission, UserNotification


class SharedFolderFlowTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner',
            email='owner@example.com',
            password='password123'
        )
        self.collaborator = User.objects.create_user(
            username='collaborator',
            email='collaborator@example.com',
            password='password123'
        )
        self.folder = File.objects.create(
            name='Team Folder',
            owner=self.owner,
            mime_type='folder'
        )

    def test_writer_can_upload_into_shared_folder(self):
        Permission.objects.create(
            file=self.folder,
            grantee_user=self.collaborator,
            grantee_email=self.collaborator.email,
            permission_type='user',
            role='writer'
        )

        self.client.force_authenticate(self.collaborator)
        upload = SimpleUploadedFile('notes.txt', b'hello', content_type='text/plain')
        response = self.client.post(
            '/api/v1/files/upload_multiple/',
            {'parent': str(self.folder.id), 'files': [upload]},
            format='multipart'
        )

        self.assertEqual(response.status_code, 201)
        child = File.objects.get(name='notes.txt')
        self.assertEqual(child.parent_id, self.folder.id)
        self.assertEqual(child.owner_id, self.collaborator.id)

        self.client.force_authenticate(self.owner)
        children = self.client.get(f'/api/v1/files/{self.folder.id}/children/')
        self.assertEqual(children.status_code, 200)
        self.assertEqual(children.data[0]['name'], 'notes.txt')

    def test_reader_cannot_upload_into_shared_folder(self):
        Permission.objects.create(
            file=self.folder,
            grantee_user=self.collaborator,
            grantee_email=self.collaborator.email,
            permission_type='user',
            role='reader'
        )

        self.client.force_authenticate(self.collaborator)
        upload = SimpleUploadedFile('notes.txt', b'hello', content_type='text/plain')
        response = self.client.post(
            '/api/v1/files/upload_multiple/',
            {'parent': str(self.folder.id), 'files': [upload]},
            format='multipart'
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(File.objects.filter(name='notes.txt').exists())

    def test_share_requires_recipient_confirmation_before_listing(self):
        self.client.force_authenticate(self.owner)
        share_response = self.client.post(
            '/api/v1/permissions/',
            {
                'file': str(self.folder.id),
                'grantee_email': self.collaborator.email,
                'permission_type': 'user',
                'role': 'reader',
            },
            format='json'
        )
        self.assertEqual(share_response.status_code, 201)

        notification = UserNotification.objects.get(user=self.collaborator)
        self.assertEqual(notification.share_status, UserNotification.SHARE_PENDING)

        self.client.force_authenticate(self.collaborator)
        pending_files = self.client.get('/api/v1/files/')
        self.assertEqual(pending_files.status_code, 200)
        self.assertFalse(any(str(item['id']) == str(self.folder.id) for item in pending_files.data['results']))

        accept_response = self.client.post(f'/api/v1/users/notifications/{notification.id}/accept_share/')
        self.assertEqual(accept_response.status_code, 200)

        accepted_files = self.client.get('/api/v1/files/')
        self.assertEqual(accepted_files.status_code, 200)
        self.assertTrue(any(str(item['id']) == str(self.folder.id) for item in accepted_files.data['results']))

    def test_clear_share_invitation_removes_access(self):
        self.client.force_authenticate(self.owner)
        share_response = self.client.post(
            '/api/v1/permissions/',
            {
                'file': str(self.folder.id),
                'grantee_email': self.collaborator.email,
                'permission_type': 'user',
                'role': 'reader',
            },
            format='json'
        )
        self.assertEqual(share_response.status_code, 201)

        notification = UserNotification.objects.get(user=self.collaborator)
        self.client.force_authenticate(self.collaborator)
        decline_response = self.client.post(f'/api/v1/users/notifications/{notification.id}/decline_share/')
        self.assertEqual(decline_response.status_code, 200)

        files_response = self.client.get('/api/v1/files/')
        self.assertEqual(files_response.status_code, 200)
        self.assertFalse(any(str(item['id']) == str(self.folder.id) for item in files_response.data['results']))
        self.assertTrue(Permission.objects.get(file=self.folder, grantee_user=self.collaborator).deleted)

    def test_legacy_notification_without_permission_can_be_confirmed(self):
        Permission.objects.create(
            file=self.folder,
            grantee_user=self.collaborator,
            grantee_email=self.collaborator.email,
            permission_type='user',
            role='reader'
        )
        notification = UserNotification.objects.create(
            user=self.collaborator,
            notification_type='share_received',
            title='New file shared with you',
            body=f"{self.owner.username} shared '{self.folder.name}' with you as reader."
        )

        self.client.force_authenticate(self.collaborator)
        response = self.client.post(f'/api/v1/users/notifications/{notification.id}/accept_share/')
        self.assertEqual(response.status_code, 200)

        notification.refresh_from_db()
        self.assertIsNotNone(notification.share_permission)
        self.assertEqual(notification.share_status, UserNotification.SHARE_ACCEPTED)

    def test_legacy_notification_can_restore_deleted_permission_on_confirm(self):
        permission = Permission.objects.create(
            file=self.folder,
            grantee_user=self.collaborator,
            grantee_email=self.collaborator.email,
            permission_type='user',
            role='reader',
            deleted=True
        )
        notification = UserNotification.objects.create(
            user=self.collaborator,
            notification_type='share_received',
            title='New file shared with you',
            body=f"{self.owner.username} shared '{self.folder.name}' with you as reader."
        )

        self.client.force_authenticate(self.collaborator)
        response = self.client.post(f'/api/v1/users/notifications/{notification.id}/accept_share/')
        self.assertEqual(response.status_code, 200)

        permission.refresh_from_db()
        notification.refresh_from_db()
        self.assertFalse(permission.deleted)
        self.assertEqual(notification.share_permission_id, permission.id)
        self.assertEqual(notification.share_status, UserNotification.SHARE_ACCEPTED)

    def test_orphaned_legacy_notification_can_be_cleared(self):
        notification = UserNotification.objects.create(
            user=self.collaborator,
            notification_type='share_received',
            title='New file shared with you',
            body=f"{self.owner.username} shared 'missing.pdf' with you as reader."
        )

        self.client.force_authenticate(self.collaborator)
        response = self.client.post(f'/api/v1/users/notifications/{notification.id}/decline_share/')
        self.assertEqual(response.status_code, 200)

        notification.refresh_from_db()
        self.assertEqual(notification.share_status, UserNotification.SHARE_DECLINED)

    def test_recipient_delete_removes_shared_item_without_trashing_owner_file(self):
        permission = Permission.objects.create(
            file=self.folder,
            grantee_user=self.collaborator,
            grantee_email=self.collaborator.email,
            permission_type='user',
            role='reader'
        )
        UserNotification.objects.create(
            user=self.collaborator,
            notification_type='share_received',
            title='New file shared with you',
            body=f"{self.owner.username} shared '{self.folder.name}' with you as reader.",
            share_permission=permission,
            share_status=UserNotification.SHARE_ACCEPTED,
        )

        self.client.force_authenticate(self.collaborator)
        response = self.client.post(f'/api/v1/files/{self.folder.id}/trash/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['removed_share'])

        self.folder.refresh_from_db()
        permission.refresh_from_db()
        self.assertFalse(self.folder.trashed)
        self.assertTrue(permission.deleted)

        collaborator_files = self.client.get('/api/v1/files/')
        self.assertFalse(any(str(item['id']) == str(self.folder.id) for item in collaborator_files.data['results']))

        self.client.force_authenticate(self.owner)
        owner_files = self.client.get('/api/v1/files/')
        self.assertTrue(any(str(item['id']) == str(self.folder.id) for item in owner_files.data['results']))
