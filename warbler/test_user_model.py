"""User model tests."""

# Run these tests like:
#
#    python -m unittest test_user_model.py

import os
from unittest import TestCase
from sqlalchemy.exc import IntegrityError
from models import db, User, Message, Follows
from app import app

# Set an environmental variable to use a different test database
os.environ['DATABASE_URL'] = "postgresql:///warbler-test"

# Create our tables
db.create_all()


class UserModelTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""
        User.query.delete()
        Message.query.delete()
        Follows.query.delete()

        self.client = app.test_client()

        # Add sample users
        self.user1 = User.signup("testuser1", "test1@test.com", "password", None)
        self.user2 = User.signup("testuser2", "test2@test.com", "password", None)
        db.session.commit()

    def tearDown(self):
        """Rollback session after each test."""
        db.session.rollback()

    def test_user_model(self):
        """Does basic model work?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        db.session.add(u)
        db.session.commit()

        # User should have no messages & no followers
        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)

    def test_repr(self):
        """Does the repr method work as expected?"""
        self.assertEqual(repr(self.user1), f"<User #{self.user1.id}: testuser1, test1@test.com>")

    def test_is_following(self):
        """Does is_following successfully detect following relationships?"""
        self.user1.following.append(self.user2)
        db.session.commit()

        self.assertTrue(self.user1.is_following(self.user2))
        self.assertFalse(self.user2.is_following(self.user1))

    def test_is_followed_by(self):
        """Does is_followed_by successfully detect follower relationships?"""
        self.user2.following.append(self.user1)
        db.session.commit()

        self.assertTrue(self.user1.is_followed_by(self.user2))
        self.assertFalse(self.user2.is_followed_by(self.user1))

    def test_signup(self):
        """Does User.signup successfully create a new user?"""
        user = User.signup("newuser", "new@test.com", "password", None)
        db.session.commit()

        self.assertIsNotNone(user.id)
        self.assertEqual(user.username, "newuser")
        self.assertEqual(user.email, "new@test.com")
        self.assertNotEqual(user.password, "password")  # Password should be hashed

    def test_signup_fail(self):
        """Does User.signup fail with invalid data?"""
        invalid_user = User.signup(None, "new@test.com", "password", None)

        with self.assertRaises(IntegrityError):
            db.session.commit()

    def test_authenticate(self):
        """Does User.authenticate successfully return a user with valid credentials?"""
        user = User.authenticate("testuser1", "password")
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "testuser1")

    def test_authenticate_invalid_username(self):
        """Does User.authenticate fail to return a user when the username is invalid?"""
        self.assertFalse(User.authenticate("wrongusername", "password"))

    def test_authenticate_invalid_password(self):
        """Does User.authenticate fail to return a user when the password is invalid?"""
        self.assertFalse(User.authenticate("testuser1", "wrongpassword"))