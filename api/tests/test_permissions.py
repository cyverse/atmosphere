"""
tests for custom permission classes
"""
import unittest
import mock

from api.permissions import CanEditOrReadOnly
from api.tests.factories import UserFactory, AnonymousUserFactory


class TestCanEditOrReadOnly(unittest.TestCase):
    def setUp(self):
        self.permissions = CanEditOrReadOnly()
        self.user = UserFactory.create()
        self.admin = UserFactory.create(is_staff=True)
        self.creator = UserFactory.create()
        self.anonymous_user = AnonymousUserFactory.create()
        self.obj = mock.Mock()
        self.obj.created_by = self.creator
        self.request = mock.Mock()
        self.view= mock.Mock()

    def test_creator_can_edit(self):
        """
        The creator is authorized.
        """
        self.request.user = self.creator
        assert self.permissions.has_object_permission(self.request, self.view, self.obj)

    def test_admin_can_edit(self):
        """
        Admin user is authorized.
        """
        self.request.user = self.admin
        assert self.permissions.has_object_permission(self.request, self.view, self.obj)

    def test_user_cannot_edit(self):
        """
        User is not authorized.
        """
        self.request.user = self.user
        assert not self.permissions.has_object_permission(self.request, self.view, self.obj)

    def test_user_can_view(self):
        """
        User is not authorized.
        """
        self.request.user = self.user
        self.request.method = "GET"
        assert self.permissions.has_object_permission(self.request, self.view, self.obj)

    def test_anonymous_user_cannot_edit(self):
        """
        Anonymous user is not authorized.
        """
        self.request.user = self.anonymous_user
        assert not self.permissions.has_object_permission(self.request, self.view, self.obj)

    def test_anonymous_user_can_view(self):
        """
        Anonymous user is not authorized.
        """
        self.request.user = self.anonymous_user
        self.request.method = "GET"
        assert self.permissions.has_object_permission(self.request, self.view, self.obj)
